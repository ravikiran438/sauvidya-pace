# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the active-augmentation profile extension (AUG-1..AUG-6)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pace.extensions.augmentation_profile import (
    AugmentationAction,
    AugmentationAxis,
    AugmentationProfile,
    AxisKind,
    AxisRevertedEvent,
    EmergencyTrigger,
    HandoffEvent,
    Mediation,
    AugmentationError,
    StepUpEndReason,
    StepUpEvent,
    audit_action,
    check_emergency_boundary,
    check_identity_preservation,
    check_reversibility,
    check_skill_maintenance,
    check_step_up,
    check_step_up_grant,
    check_step_up_nudge,
)


def _profile(
    principal_id: str = "user-123",
    axes: list[tuple[str, AxisKind]] | None = None,
    triggers: list[str] | None = None,
    identity_consent: bool = False,
    version: str = "v1",
) -> AugmentationProfile:
    axes = axes or [
        ("social_interpretation", AxisKind.COMPENSATE),
        ("executive_function", AxisKind.COMPENSATE),
        ("special_interest", AxisKind.AMPLIFY),
        ("independent_email", AxisKind.PRESERVE),
    ]
    triggers = triggers or ["medical_keyword"]
    return AugmentationProfile(
        principal_id=principal_id,
        version=version,
        pcp_version="2026-04-25.v1",
        axes=[AugmentationAxis(name=n, kind=k) for n, k in axes],
        emergency_triggers=[
            EmergencyTrigger(name=t, description=f"trigger: {t}") for t in triggers
        ],
        identity_consent=identity_consent,
        declared_at=datetime.now(timezone.utc),
        declared_by="principal",
    )


def _action(
    principal_id: str = "user-123",
    axis_name: str = "social_interpretation",
    mediation: Mediation = Mediation.AGENT_COMPENSATED,
    alters_identity: bool = False,
    at: datetime | None = None,
    profile_version: str = "v1",
    task_id: str | None = None,
) -> AugmentationAction:
    return AugmentationAction(
        principal_id=principal_id,
        axis_name=axis_name,
        mediation=mediation,
        profile_version=profile_version,
        task_id=task_id,
        alters_identity=alters_identity,
        description="test",
        at=at or datetime.now(timezone.utc),
    )


# ─────────────────────────────────────────────────────────────────────
# AUG-1 Reversibility
# ─────────────────────────────────────────────────────────────────────


class TestReversibility:
    def test_no_reversion_passes(self):
        check_reversibility(_action(), [])

    def test_action_after_reversion_rejected(self):
        now = datetime.now(timezone.utc)
        ev = AxisRevertedEvent(
            principal_id="user-123",
            axis_name="social_interpretation",
            reverted_at=now - timedelta(minutes=5),
            reverted_by="principal",
        )
        action = _action(at=now)
        with pytest.raises(AugmentationError, match="was reverted"):
            check_reversibility(action, [ev])

    def test_action_before_reversion_passes(self):
        now = datetime.now(timezone.utc)
        ev = AxisRevertedEvent(
            principal_id="user-123",
            axis_name="social_interpretation",
            reverted_at=now + timedelta(minutes=5),
            reverted_by="principal",
        )
        action = _action(at=now)
        check_reversibility(action, [ev])

    def test_user_direct_unaffected_by_reversion(self):
        now = datetime.now(timezone.utc)
        ev = AxisRevertedEvent(
            principal_id="user-123",
            axis_name="social_interpretation",
            reverted_at=now - timedelta(minutes=5),
            reverted_by="principal",
        )
        action = _action(mediation=Mediation.USER_DIRECT, at=now)
        check_reversibility(action, [ev])  # user_direct is always allowed

    def test_reversion_for_other_principal_doesnt_apply(self):
        now = datetime.now(timezone.utc)
        ev = AxisRevertedEvent(
            principal_id="other-user",
            axis_name="social_interpretation",
            reverted_at=now - timedelta(minutes=5),
            reverted_by="principal",
        )
        check_reversibility(_action(at=now), [ev])


# ─────────────────────────────────────────────────────────────────────
# AUG-3 Identity Preservation
# ─────────────────────────────────────────────────────────────────────


class TestIdentityPreservation:
    def test_no_identity_alteration_passes(self):
        profile = _profile(identity_consent=False)
        check_identity_preservation(profile, _action(alters_identity=False))

    def test_identity_alteration_with_consent_passes(self):
        profile = _profile(identity_consent=True)
        check_identity_preservation(profile, _action(alters_identity=True))

    def test_identity_alteration_without_consent_rejected(self):
        profile = _profile(identity_consent=False)
        with pytest.raises(AugmentationError, match="identity_consent"):
            check_identity_preservation(profile, _action(alters_identity=True))

    def test_user_direct_with_alteration_unaffected(self):
        # AUG-3 only constrains agent-mediated actions. A user_direct
        # "alteration" is logically the user expressing themselves.
        profile = _profile(identity_consent=False)
        check_identity_preservation(
            profile,
            _action(mediation=Mediation.USER_DIRECT, alters_identity=True),
        )

    def test_principal_id_mismatch_rejected(self):
        profile = _profile(principal_id="user-A", identity_consent=True)
        action = _action(principal_id="user-B", alters_identity=True)
        with pytest.raises(AugmentationError, match="does not match"):
            check_identity_preservation(profile, action)


# ─────────────────────────────────────────────────────────────────────
# AUG-4 Skill Maintenance
# ─────────────────────────────────────────────────────────────────────


class TestSkillMaintenance:
    def test_compensate_axis_passes(self):
        profile = _profile()
        check_skill_maintenance(profile, _action(axis_name="social_interpretation"))

    def test_amplify_axis_passes(self):
        profile = _profile()
        check_skill_maintenance(
            profile,
            _action(
                axis_name="special_interest",
                mediation=Mediation.AGENT_AMPLIFIED,
            ),
        )

    def test_preserve_axis_compensate_rejected(self):
        profile = _profile()
        with pytest.raises(AugmentationError, match="declared 'preserve'"):
            check_skill_maintenance(
                profile, _action(axis_name="independent_email")
            )

    def test_preserve_axis_amplify_rejected(self):
        profile = _profile()
        with pytest.raises(AugmentationError, match="declared 'preserve'"):
            check_skill_maintenance(
                profile,
                _action(
                    axis_name="independent_email",
                    mediation=Mediation.AGENT_AMPLIFIED,
                ),
            )

    def test_preserve_axis_user_direct_passes(self):
        profile = _profile()
        # User can still act directly on a preserved axis. AUG-4 only
        # forbids agent compensation/amplification.
        check_skill_maintenance(
            profile,
            _action(axis_name="independent_email", mediation=Mediation.USER_DIRECT),
        )

    def test_undeclared_axis_rejected(self):
        profile = _profile()
        with pytest.raises(AugmentationError, match="not declared in profile"):
            check_skill_maintenance(
                profile, _action(axis_name="never-heard-of-this")
            )


# ─────────────────────────────────────────────────────────────────────
# AUG-5 Emergency Boundary
# ─────────────────────────────────────────────────────────────────────


class TestEmergencyBoundary:
    def _handoff(
        self,
        principal_id: str = "user-123",
        fired_at: datetime | None = None,
        ack_at: datetime | None = None,
    ) -> HandoffEvent:
        return HandoffEvent(
            principal_id=principal_id,
            trigger_name="medical_keyword",
            fired_at=fired_at or datetime.now(timezone.utc),
            human_acknowledged_at=ack_at,
            human_acknowledged_by="ops" if ack_at else None,
        )

    def test_no_handoff_passes(self):
        check_emergency_boundary(_action(), [])

    def test_action_after_unacked_handoff_rejected(self):
        now = datetime.now(timezone.utc)
        h = self._handoff(fired_at=now - timedelta(minutes=5))
        with pytest.raises(AugmentationError, match="awaiting human"):
            check_emergency_boundary(_action(at=now), [h])

    def test_action_after_ack_passes(self):
        now = datetime.now(timezone.utc)
        h = self._handoff(
            fired_at=now - timedelta(minutes=10),
            ack_at=now - timedelta(minutes=2),
        )
        check_emergency_boundary(_action(at=now), [h])

    def test_action_before_handoff_passes(self):
        now = datetime.now(timezone.utc)
        h = self._handoff(fired_at=now + timedelta(minutes=5))
        check_emergency_boundary(_action(at=now), [h])

    def test_user_direct_unaffected_by_handoff(self):
        now = datetime.now(timezone.utc)
        h = self._handoff(fired_at=now - timedelta(minutes=5))
        check_emergency_boundary(
            _action(mediation=Mediation.USER_DIRECT, at=now), [h]
        )

    def test_handoff_for_other_principal_unaffected(self):
        now = datetime.now(timezone.utc)
        h = self._handoff(
            principal_id="other-user", fired_at=now - timedelta(minutes=5)
        )
        check_emergency_boundary(_action(at=now), [h])


# ─────────────────────────────────────────────────────────────────────
# Bundled audit
# ─────────────────────────────────────────────────────────────────────


class TestBundledAudit:
    def test_clean_action_passes_all_checks(self):
        profile = _profile()
        audit_action(profile, _action())

    def test_preserve_axis_fails_audit(self):
        profile = _profile()
        with pytest.raises(AugmentationError):
            audit_action(profile, _action(axis_name="independent_email"))

    def test_identity_alteration_without_consent_fails_audit(self):
        profile = _profile(identity_consent=False)
        with pytest.raises(AugmentationError):
            audit_action(profile, _action(alters_identity=True))


# ─────────────────────────────────────────────────────────────────────
# Type-level sanity
# ─────────────────────────────────────────────────────────────────────


class TestTypes:
    def test_axis_names_must_be_unique(self):
        with pytest.raises(ValueError, match="declared twice"):
            AugmentationProfile(
                principal_id="p",
                version="v1",
                pcp_version="v1",
                axes=[
                    AugmentationAxis(name="x", kind=AxisKind.COMPENSATE),
                    AugmentationAxis(name="x", kind=AxisKind.AMPLIFY),
                ],
                declared_at=datetime.now(timezone.utc),
                declared_by="principal",
            )

    def test_profile_axis_lookup(self):
        profile = _profile()
        assert profile.axis_kind("social_interpretation") == AxisKind.COMPENSATE
        assert profile.axis_kind("special_interest") == AxisKind.AMPLIFY
        assert profile.axis_kind("independent_email") == AxisKind.PRESERVE
        assert profile.axis_kind("does-not-exist") is None

    def test_action_is_immutable(self):
        action = _action()
        with pytest.raises(ValueError):
            action.alters_identity = True  # type: ignore[misc]

    def test_trigger_names(self):
        profile = _profile(triggers=["medical_keyword", "financial_threshold"])
        assert profile.trigger_names() == {"medical_keyword", "financial_threshold"}


# ─────────────────────────────────────────────────────────────────────
# AUG-4 profile versions (the history TLC flagged)
# ─────────────────────────────────────────────────────────────────────


class TestSkillMaintenanceVersions:
    def test_earlier_help_stays_legal_after_axis_becomes_preserve(self):
        """compensate -> agent helps -> principal re-declares preserve."""
        v1 = _profile(version="v1")
        v2 = _profile(
            version="v2",
            axes=[("social_interpretation", AxisKind.PRESERVE)],
        )
        earlier = _action(profile_version="v1")
        check_skill_maintenance(v1, earlier)
        with pytest.raises(AugmentationError, match="audit it against that version"):
            check_skill_maintenance(v2, earlier)

    def test_later_help_on_preserved_axis_rejected(self):
        v2 = _profile(
            version="v2",
            axes=[("social_interpretation", AxisKind.PRESERVE)],
        )
        with pytest.raises(AugmentationError, match="AUG-4"):
            check_skill_maintenance(v2, _action(profile_version="v2"))

    def test_identity_check_also_requires_matching_version(self):
        profile = _profile(identity_consent=True, version="v2")
        action = _action(alters_identity=True, profile_version="v1")
        with pytest.raises(AugmentationError, match="AUG-3"):
            check_identity_preservation(profile, action)


# ─────────────────────────────────────────────────────────────────────
# AUG-6 Task-Scoped Step-Up
# ─────────────────────────────────────────────────────────────────────

T0 = datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)


def _step_up(
    axis_name: str = "social_interpretation",
    task_id: str = "task-1",
    expires_in: timedelta = timedelta(minutes=30),
    nudged_at: datetime | None = None,
    ended_at: datetime | None = None,
    end_reason: StepUpEndReason | None = None,
) -> StepUpEvent:
    return StepUpEvent(
        principal_id="user-123",
        axis_name=axis_name,
        task_id=task_id,
        granted_at=T0,
        expires_at=T0 + expires_in,
        nudged_at=nudged_at,
        ended_at=ended_at,
        end_reason=end_reason,
    )


class TestStepUp:
    def test_blocks_agent_on_same_axis_and_task(self):
        action = _action(task_id="task-1", at=T0 + timedelta(minutes=5))
        with pytest.raises(AugmentationError, match="AUG-6"):
            check_step_up(action, [_step_up()])

    def test_other_task_keeps_default_help(self):
        check_step_up(
            _action(task_id="task-2", at=T0 + timedelta(minutes=5)), [_step_up()]
        )

    def test_other_axis_keeps_default_help(self):
        check_step_up(
            _action(
                axis_name="executive_function",
                task_id="task-1",
                at=T0 + timedelta(minutes=5),
            ),
            [_step_up()],
        )

    def test_user_direct_always_allowed(self):
        check_step_up(
            _action(
                mediation=Mediation.USER_DIRECT,
                task_id="task-1",
                at=T0 + timedelta(minutes=5),
            ),
            [_step_up()],
        )

    def test_action_before_step_up_allowed(self):
        check_step_up(
            _action(task_id="task-1", at=T0 - timedelta(minutes=1)), [_step_up()]
        )

    def test_expiry_does_not_resume_help(self):
        """No silent resumption: past expires_at the block still holds."""
        action = _action(task_id="task-1", at=T0 + timedelta(hours=2))
        with pytest.raises(AugmentationError, match="AUG-6"):
            check_step_up(action, [_step_up()])

    def test_task_end_closes_step_up(self):
        ev = _step_up(
            ended_at=T0 + timedelta(minutes=10),
            end_reason=StepUpEndReason.TASK_ENDED,
        )
        check_step_up(_action(task_id="task-1", at=T0 + timedelta(minutes=11)), [ev])

    def test_principal_can_end_step_up_after_nudge(self):
        ev = _step_up(
            expires_in=timedelta(minutes=30),
            nudged_at=T0 + timedelta(minutes=31),
            ended_at=T0 + timedelta(minutes=33),
            end_reason=StepUpEndReason.PRINCIPAL_ENDED,
        )
        check_step_up(_action(task_id="task-1", at=T0 + timedelta(minutes=34)), [ev])

    def test_nudge_due_only_after_time_limit(self):
        ev = _step_up(expires_in=timedelta(minutes=30))
        check_step_up_nudge(ev, T0 + timedelta(minutes=29))
        with pytest.raises(AugmentationError, match="nudge the principal"):
            check_step_up_nudge(ev, T0 + timedelta(minutes=30))

    def test_no_nudge_once_nudged_or_ended(self):
        nudged = _step_up(nudged_at=T0 + timedelta(minutes=31))
        check_step_up_nudge(nudged, T0 + timedelta(hours=1))
        ended = _step_up(
            ended_at=T0 + timedelta(minutes=5),
            end_reason=StepUpEndReason.TASK_ENDED,
        )
        check_step_up_nudge(ended, T0 + timedelta(hours=1))

    def test_grant_rejected_on_preserve_axis(self):
        with pytest.raises(AugmentationError, match="nothing to step up"):
            check_step_up_grant(_profile(), _step_up(axis_name="independent_email"))

    def test_grant_allowed_on_compensate_axis(self):
        check_step_up_grant(_profile(), _step_up())

    def test_only_principal_can_grant(self):
        with pytest.raises(ValueError):
            StepUpEvent(
                principal_id="user-123",
                axis_name="social_interpretation",
                task_id="task-1",
                granted_by="guardian:g1",
                granted_at=T0,
                expires_at=T0 + timedelta(minutes=30),
            )

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"expires_in": timedelta(0)},
            {"ended_at": T0 + timedelta(minutes=5)},
            {"end_reason": StepUpEndReason.TASK_ENDED},
            {"nudged_at": T0 + timedelta(minutes=5)},
        ],
    )
    def test_incoherent_timelines_rejected(self, kwargs):
        with pytest.raises(ValueError):
            _step_up(**kwargs)

    def test_audit_action_runs_step_up_check(self):
        with pytest.raises(AugmentationError, match="AUG-6"):
            audit_action(
                _profile(),
                _action(task_id="task-1", at=T0 + timedelta(minutes=5)),
                step_up_events=[_step_up()],
            )
