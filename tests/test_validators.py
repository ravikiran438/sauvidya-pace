# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for PACE validators."""

import pytest
from pace.types import *
from pace.validators import *


def _pcp(decision_capacity=DecisionCapacity.FLUCTUATING, lang="te"):
    return PrincipalCapabilityProfile(
        principal_id="p1", version="v1",
        declared_at="2026-04-17T10:00:00Z", declared_by="guardian:g1",
        language=[LanguageFluency(code=lang, fluency=1.0)],
        decision_capacity=decision_capacity,
    )


def _modality(lang="te", pcp_version="v1"):
    return InteractionModality(
        agent_id="a1", principal_id="p1", pcp_version=pcp_version,
        modality_plan=ModalityPlan(
            primary_channel=PrimaryChannel.VOICE,
            language=lang, max_options=2, timeout_seconds=300,
        ),
    )


def _ccc(recommendation=CapacityRecommendation.PROCEED):
    return ConsentCapacityCheck(
        principal_id="p1", timestamp="2026-04-17T10:15:00Z",
        capacity_signal=0.82, confidence=0.75,
        assessment_method=AssessmentMethod.PASSIVE,
        pcp_version="v1", recommendation=recommendation,
    )


def _contract(lang="te"):
    return AdaptiveInteractionContract(
        principal_id="p1", pcp_version="v1",
        interaction_rules=InteractionRules(
            language=lang,
            valid_time_windows=[
                TimeWindow(start="09:00", end="11:00"),
                TimeWindow(start="14:00", end="16:00"),
            ],
            sundown_block=TimeWindow(start="17:00", end="08:00"),
        ),
    )


# ─── IM-1: Modality Precondition ─────────────────────────────────────

class TestModalityPrecondition:
    def test_valid_modality(self):
        validate_im_precondition(_modality(), _pcp())

    def test_no_modality_fails(self):
        with pytest.raises(ModalityPreconditionError, match="IM-1"):
            validate_im_precondition(None, _pcp())

    def test_version_mismatch_fails(self):
        with pytest.raises(ModalityPreconditionError, match="IM-1"):
            validate_im_precondition(_modality(pcp_version="v0"), _pcp())


# ─── IM-2: Language Match ────────────────────────────────────────────

class TestLanguageMatch:
    def test_matching_language(self):
        validate_language_match(_modality(lang="te"), _pcp(lang="te"))

    def test_english_default_blocked(self):
        with pytest.raises(LanguageMismatchError, match="IM-2"):
            validate_language_match(_modality(lang="en"), _pcp(lang="te"))


# ─── CCC-1: Capacity Gate ────────────────────────────────────────────

class TestCCCGate:
    def test_fluctuating_with_proceed(self):
        validate_ccc_gate(_pcp(DecisionCapacity.FLUCTUATING), _ccc())

    def test_fluctuating_with_simplify(self):
        validate_ccc_gate(
            _pcp(DecisionCapacity.FLUCTUATING),
            _ccc(CapacityRecommendation.SIMPLIFY),
        )

    def test_fluctuating_no_check_fails(self):
        with pytest.raises(CCCGateError, match="CCC-1"):
            validate_ccc_gate(_pcp(DecisionCapacity.FLUCTUATING), None)

    def test_fluctuating_defer_fails(self):
        with pytest.raises(CCCGateError, match="CCC-1"):
            validate_ccc_gate(
                _pcp(DecisionCapacity.FLUCTUATING),
                _ccc(CapacityRecommendation.DEFER),
            )

    def test_stable_no_check_ok(self):
        validate_ccc_gate(_pcp(DecisionCapacity.STABLE), None)

    def test_guardian_required_no_check_fails(self):
        with pytest.raises(CCCGateError):
            validate_ccc_gate(_pcp(DecisionCapacity.GUARDIAN_REQUIRED), None)


# ─── CCC-2: Privacy ─────────────────────────────────────────────────

class TestCCCPrivacy:
    def test_no_leak(self):
        validate_ccc_privacy(_ccc(), {"interaction_status", "agent_id"})

    def test_capacity_signal_leak(self):
        with pytest.raises(CCCPrivacyError, match="CCC-2"):
            validate_ccc_privacy(_ccc(), {"capacity_signal", "agent_id"})

    def test_assessment_method_leak(self):
        with pytest.raises(CCCPrivacyError, match="CCC-2"):
            validate_ccc_privacy(_ccc(), {"assessment_method"})


# ─── AIC-1: Time Window ─────────────────────────────────────────────

class TestTimeWindow:
    def test_valid_morning_time(self):
        validate_time_window(_contract(), "10:00")

    def test_valid_afternoon_time(self):
        validate_time_window(_contract(), "15:00")

    def test_sundown_blocked(self):
        with pytest.raises(TimeWindowViolationError, match="AIC-1"):
            validate_time_window(_contract(), "19:00")

    def test_outside_all_windows(self):
        with pytest.raises(TimeWindowViolationError, match="AIC-1"):
            validate_time_window(_contract(), "12:00")

    def test_emergency_overrides(self):
        validate_time_window(_contract(), "19:00", is_emergency=True)


# ─── AIC-2: Option Count ────────────────────────────────────────────

class TestOptionCount:
    def test_within_limit(self):
        validate_option_count(_contract(), 2)

    def test_single_option(self):
        validate_option_count(_contract(), 1)

    def test_over_limit(self):
        with pytest.raises(OptionOverloadError, match="AIC-2"):
            validate_option_count(_contract(), 5)
