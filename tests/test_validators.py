# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for PACE validators."""

from datetime import datetime
from zoneinfo import ZoneInfo

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
            timezone="Asia/Kolkata",
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


def _lakshmi(pinned: bool = True, en: float = 0.3, hi: float | None = None):
    """The paper's worked example: Telugu 1.0, English 0.3."""
    languages = [
        LanguageFluency(code="te", fluency=1.0),
        LanguageFluency(code="en", fluency=en),
    ]
    if hi is not None:
        languages.append(LanguageFluency(code="hi", fluency=hi))
    return PrincipalCapabilityProfile(
        principal_id="p1", version="v1",
        declared_at="2026-10-01T10:00:00+05:30", declared_by="guardian:g1",
        language=languages,
        decision_capacity=DecisionCapacity.FLUCTUATING,
        adaptations_required=["voice_primary", "language:te"] if pinned else [],
    )


class TestLanguageRule:
    def test_paper_example_english_call_rejected(self):
        with pytest.raises(LanguageMismatchError, match="pins language:te"):
            validate_language_match(_modality(lang="en"), _lakshmi())

    def test_pin_wins_over_fluency(self):
        pcp = _lakshmi(pinned=True, en=0.9)
        with pytest.raises(LanguageMismatchError, match="pins"):
            validate_language_match(_modality(lang="en"), pcp)
        validate_language_match(_modality(lang="te"), pcp)

    def test_without_pin_low_fluency_rejected(self):
        with pytest.raises(LanguageMismatchError, match="below the floor"):
            validate_language_match(_modality(lang="en"), _lakshmi(pinned=False))

    def test_without_pin_strong_second_language_allowed(self):
        validate_language_match(
            _modality(lang="hi"), _lakshmi(pinned=False, hi=0.9)
        )

    def test_floor_comes_from_contract(self):
        pcp = _lakshmi(pinned=False, en=0.6)
        with pytest.raises(LanguageMismatchError, match="below the floor of 0.70"):
            validate_language_match(_modality(lang="en"), pcp)
        lenient = AdaptiveInteractionContract(
            principal_id="p1", pcp_version="v1",
            interaction_rules=InteractionRules(language="te", timezone="Asia/Kolkata", min_language_fluency=0.5),
        )
        validate_language_match(_modality(lang="en"), pcp, lenient)

    def test_error_names_next_rung(self):
        modality = _modality(lang="en")
        modality = modality.model_copy(update={"escalation_target": "guardian:g1"})
        with pytest.raises(LanguageMismatchError) as err:
            validate_language_match(modality, _lakshmi())
        assert "sub-agent that speaks one of ['te']" in str(err.value)
        assert "escalate to guardian:g1" in str(err.value)

    def test_no_language_meets_floor(self):
        pcp = PrincipalCapabilityProfile(
            principal_id="p1", version="v1",
            declared_at="2026-10-01T10:00:00Z", declared_by="principal",
            language=[LanguageFluency(code="te", fluency=0.4)],
        )
        with pytest.raises(LanguageMismatchError, match="no language"):
            validate_language_match(_modality(lang="te"), pcp)

    def test_acceptable_languages(self):
        assert acceptable_languages(_lakshmi()) == {"te"}
        assert acceptable_languages(_lakshmi(pinned=False, hi=0.9)) == {"te", "hi"}

    def test_contract_cannot_bind_ruled_out_language(self):
        english = AdaptiveInteractionContract(
            principal_id="p1", pcp_version="v1",
            interaction_rules=InteractionRules(language="en", timezone="Asia/Kolkata"),
        )
        with pytest.raises(LanguageMismatchError, match="AIC"):
            validate_contract_language(english, _lakshmi())
        validate_contract_language(_contract(lang="te"), _lakshmi())


# ─── CCC-4: Relay carries the question, not the consent ─────────────

def _annotation(relayed_by=None, ccc_performed=True, method=AssessmentMethod.PASSIVE):
    ccc = (
        dict(
            ccc_capacity_signal=0.8,
            ccc_recommendation=CapacityRecommendation.PROCEED,
            ccc_assessment_method=method,
        )
        if ccc_performed
        else {}
    )
    return PACEConsentAnnotation(
        annotation_id="ann-1", consent_record_id="cr-1",
        principal_id="p1", pcp_version="v1",
        relayed_by=relayed_by, ccc_performed=ccc_performed,
        interaction_modality=ModalityPlan(primary_channel=PrimaryChannel.VOICE, language="te"),
        annotated_at="2026-10-09T10:00:00Z", **ccc,
    )


class TestRelayConsent:
    def test_direct_consent_unaffected(self):
        validate_relay_consent(_pcp(), _annotation(relayed_by=None, ccc_performed=False))

    def test_relay_with_principal_ccc_passes(self):
        validate_relay_consent(_pcp(), _annotation(relayed_by="guardian:g1"))

    def test_relay_without_ccc_rejected_even_when_stable(self):
        pcp = _pcp(decision_capacity=DecisionCapacity.STABLE)
        with pytest.raises(RelayConsentError, match="CCC-4"):
            validate_relay_consent(pcp, _annotation(relayed_by="guardian:g1", ccc_performed=False))

    def test_relaying_guardian_cannot_vouch_for_capacity(self):
        ann = _annotation(relayed_by="guardian:g1", method=AssessmentMethod.GUARDIAN_CONFIRMED)
        with pytest.raises(RelayConsentError, match="also confirmed capacity"):
            validate_relay_consent(_pcp(), ann)

    def test_guardian_required_principal_exempt(self):
        pcp = _pcp(decision_capacity=DecisionCapacity.GUARDIAN_REQUIRED)
        validate_relay_consent(pcp, _annotation(relayed_by="guardian:g1", ccc_performed=False))

    def test_relayed_by_must_name_a_guardian(self):
        with pytest.raises(ValueError):
            _annotation(relayed_by="agent:a1")


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

IST = ZoneInfo("Asia/Kolkata")
CHICAGO = ZoneInfo("America/Chicago")


def _ist(hhmm: str, day: int = 10) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime(2026, 10, day, h, m, tzinfo=IST)


class TestTimeWindow:
    def test_valid_morning_time(self):
        validate_time_window(_contract(), _ist("10:00"))

    def test_valid_afternoon_time(self):
        validate_time_window(_contract(), _ist("15:00"))

    def test_sundown_blocked(self):
        with pytest.raises(TimeWindowViolationError, match="AIC-1"):
            validate_time_window(_contract(), _ist("19:00"))

    def test_outside_all_windows(self):
        with pytest.raises(TimeWindowViolationError, match="AIC-1"):
            validate_time_window(_contract(), _ist("12:00"))

    def test_emergency_overrides(self):
        validate_time_window(_contract(), _ist("19:00"), is_emergency=True)

    def test_sundown_block_wraps_past_midnight(self):
        """Sundown 17:00-08:00 with no valid windows: only the wrap
        logic can reject 02:00."""
        contract = AdaptiveInteractionContract(
            principal_id="p1", pcp_version="v1",
            interaction_rules=InteractionRules(
                language="te",
                timezone="Asia/Kolkata",
                sundown_block=TimeWindow(start="17:00", end="08:00"),
            ),
        )
        with pytest.raises(TimeWindowViolationError, match="sundown"):
            validate_time_window(contract, _ist("02:00"))
        validate_time_window(contract, _ist("08:01"))


class TestTimeZones:
    def test_agent_in_texas_is_judged_by_her_clock(self):
        """Perturbation 16: 08:30 CDT in Texas is 19:00 IST in Hyderabad,
        inside her sundown block."""
        texas_morning = datetime(2026, 10, 10, 8, 30, tzinfo=CHICAGO)
        with pytest.raises(TimeWindowViolationError, match="19:00 Asia/Kolkata"):
            validate_time_window(_contract(), texas_morning)

    def test_texas_evening_is_her_morning(self):
        """21:30 CDT is 08:00 IST the next day: still sundown (ends 08:00)."""
        with pytest.raises(TimeWindowViolationError, match="08:00 Asia/Kolkata"):
            validate_time_window(_contract(), datetime(2026, 10, 30, 21, 30, tzinfo=CHICAGO))

    def test_same_wall_clock_across_us_dst_change(self):
        """US DST ends 2026-11-01; India has no DST. The same 21:30 in
        Chicago is 08:00 IST before the change (blocked) and 09:00 IST
        after it (inside her 09:00-11:00 window)."""
        before = datetime(2026, 10, 30, 21, 30, tzinfo=CHICAGO)
        after = datetime(2026, 11, 2, 21, 30, tzinfo=CHICAGO)
        assert principal_local_time(_contract(), before).strftime("%H:%M") == "08:00"
        assert principal_local_time(_contract(), after).strftime("%H:%M") == "09:00"
        with pytest.raises(TimeWindowViolationError):
            validate_time_window(_contract(), before)
        validate_time_window(_contract(), after)

    def test_naive_timestamp_rejected(self):
        with pytest.raises(ValueError, match="zone-aware"):
            validate_time_window(_contract(), datetime(2026, 10, 10, 10, 0))

    def test_unknown_timezone_rejected(self):
        with pytest.raises(ValueError, match="unknown IANA time zone"):
            InteractionRules(language="te", timezone="Asia/Hyderabad")

    def test_error_shows_both_clocks(self):
        texas_morning = datetime(2026, 10, 10, 8, 30, tzinfo=CHICAGO)
        with pytest.raises(TimeWindowViolationError) as err:
            validate_time_window(_contract(), texas_morning)
        assert "2026-10-10T08:30-05:00 on the agent's clock" in str(err.value)


# ─── AIC-2: Option Count ────────────────────────────────────────────

class TestOptionCount:
    def test_within_limit(self):
        validate_option_count(_contract(), 2)

    def test_single_option(self):
        validate_option_count(_contract(), 1)

    def test_over_limit(self):
        with pytest.raises(OptionOverloadError, match="AIC-2"):
            validate_option_count(_contract(), 5)
