# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the active-augmentation profile extension (AUG-1..AUG-5)."""

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
    audit_action,
    check_emergency_boundary,
    check_identity_preservation,
    check_reversibility,
    check_skill_maintenance,
)


def _profile(
    principal_id: str = "user-123",
    axes: list[tuple[str, AxisKind]] | None = None,
    triggers: list[str] | None = None,
    identity_consent: bool = False,
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
) -> AugmentationAction:
    return AugmentationAction(
        principal_id=principal_id,
        axis_name=axis_name,
        mediation=mediation,
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
