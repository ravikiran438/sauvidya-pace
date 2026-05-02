# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the new PACE wire primitives.

Covers:
- AccessibilityServiceRef (the AgentCard descriptor)
- PACEConsentAnnotation (sibling to ACAP ConsentRecord)
- ActiveChallenge (tamper-evident active CCC)
- CCCTrend derivation
- PACEViolationNotice + evidence_hash helper
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pace.types import (
    PACE_EXTENSION_URI,
    AccessibilityServiceRef,
    ActiveChallenge,
    AssessmentMethod,
    CCCTrend,
    CapacityRecommendation,
    ChallengeType,
    ConsentCapacityCheck,
    EnforcementAction,
    ModalityPlan,
    PACEConsentAnnotation,
    PACEViolationNotice,
    PrimaryChannel,
    ResponseClassification,
    SLOPE_NOISE_FLOOR,
    ViolationType,
    derive_ccc_trend,
)


# --------------------------------------------------------------------------
# AccessibilityServiceRef
# --------------------------------------------------------------------------


def _ref(**overrides) -> AccessibilityServiceRef:
    base = dict(
        version="1.0.0",
        pcp_endpoint="https://orch.example.com/pace/pcp",
        aic_endpoint="https://orch.example.com/pace/aic/{principal_id}",
        violation_notice_endpoint="https://orch.example.com/pace/violations",
        supported_modalities=["voice", "text"],
        supported_languages=["en"],
    )
    base.update(overrides)
    return AccessibilityServiceRef(**base)


def test_extension_uri_is_stable():
    assert PACE_EXTENSION_URI == "https://github.com/ravikiran438/sauvidya-pace/v1"


def test_service_ref_round_trip():
    ref = _ref()
    blob = ref.model_dump_json()
    parsed = AccessibilityServiceRef.model_validate_json(blob)
    assert parsed.violation_notice_endpoint.endswith("/pace/violations")


def test_service_ref_requires_at_least_one_modality_and_language():
    with pytest.raises(ValueError):
        _ref(supported_modalities=[])
    with pytest.raises(ValueError):
        _ref(supported_languages=[])


# --------------------------------------------------------------------------
# ActiveChallenge
# --------------------------------------------------------------------------


def test_active_challenge_canonical_hash_is_deterministic():
    h1 = ActiveChallenge.hash_canonical_text("Hello, principal.")
    h2 = ActiveChallenge.hash_canonical_text("Hello, principal.   ")  # trailing ws
    assert h1 == h2  # canonical strips trailing whitespace
    assert h1.startswith("sha256:")


def test_active_challenge_round_trip():
    h = ActiveChallenge.hash_canonical_text("repeat back the amount")
    rh = ActiveChallenge.hash_canonical_text("forty two dollars")
    challenge = ActiveChallenge(
        challenge_id="ch-1",
        challenge_type=ChallengeType.CONFIRMATION_REPEAT,
        challenge_hash=h,
        response_hash=rh,
        response_window_ms=10000,
        response_received_ms=2200,
        classified_as=ResponseClassification.COMPREHENDED,
        posed_at="2026-04-30T10:00:00Z",
    )
    blob = challenge.model_dump_json()
    parsed = ActiveChallenge.model_validate_json(blob)
    assert parsed.classified_as == ResponseClassification.COMPREHENDED


def test_active_challenge_non_responsive_requires_no_received_ms():
    h = ActiveChallenge.hash_canonical_text("x")
    rh = ActiveChallenge.hash_canonical_text("")
    with pytest.raises(ValueError, match="response_received_ms"):
        ActiveChallenge(
            challenge_id="ch-1",
            challenge_type=ChallengeType.COMPREHENSION_QUESTION,
            challenge_hash=h,
            response_hash=rh,
            response_window_ms=5000,
            response_received_ms=3000,  # contradicts non-responsive
            classified_as=ResponseClassification.NON_RESPONSIVE,
            posed_at="2026-04-30T10:00:00Z",
        )


def test_active_challenge_responded_requires_received_ms():
    h = ActiveChallenge.hash_canonical_text("x")
    with pytest.raises(ValueError, match="response_received_ms"):
        ActiveChallenge(
            challenge_id="ch-1",
            challenge_type=ChallengeType.COMPREHENSION_QUESTION,
            challenge_hash=h,
            response_hash=h,
            response_window_ms=5000,
            response_received_ms=None,
            classified_as=ResponseClassification.COMPREHENDED,
            posed_at="2026-04-30T10:00:00Z",
        )


def test_active_challenge_response_cannot_exceed_window():
    h = ActiveChallenge.hash_canonical_text("x")
    with pytest.raises(ValueError, match="response_window_ms"):
        ActiveChallenge(
            challenge_id="ch-1",
            challenge_type=ChallengeType.COMPREHENSION_QUESTION,
            challenge_hash=h,
            response_hash=h,
            response_window_ms=1000,
            response_received_ms=2000,
            classified_as=ResponseClassification.COMPREHENDED,
            posed_at="2026-04-30T10:00:00Z",
        )


# --------------------------------------------------------------------------
# CCC trend
# --------------------------------------------------------------------------


def _ccc(signal: float, days_ago: float, *, base: datetime) -> ConsentCapacityCheck:
    ts = (base - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ConsentCapacityCheck(
        principal_id="p-1",
        timestamp=ts,
        capacity_signal=signal,
        confidence=0.8,
        assessment_method=AssessmentMethod.PASSIVE,
        pcp_version="1.0",
        recommendation=CapacityRecommendation.PROCEED,
    )


def test_ccc_trend_insufficient_data():
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    # only 4 samples, min_samples is 5 by default
    samples = [_ccc(0.5, i, base=now) for i in range(4)]
    assert derive_ccc_trend(samples, now=now) == CCCTrend.INSUFFICIENT_DATA


def test_ccc_trend_stable():
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    samples = [_ccc(0.6, i, base=now) for i in range(10)]
    assert derive_ccc_trend(samples, now=now) == CCCTrend.STABLE


def test_ccc_trend_declining():
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    # capacity signals dropping by 0.05/sample (ordered newest -> oldest in input)
    samples = [_ccc(0.95 - 0.05 * i, i, base=now) for i in range(10)]
    # After chronological sort (oldest first) signals go 0.50 ... 0.95 -> IMPROVING.
    # To get DECLINING we want oldest=high, newest=low:
    samples_declining = [_ccc(0.50 + 0.05 * i, i, base=now) for i in range(10)]
    assert derive_ccc_trend(samples_declining, now=now) == CCCTrend.DECLINING


def test_ccc_trend_improving():
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    samples = [_ccc(0.95 - 0.05 * i, i, base=now) for i in range(10)]
    assert derive_ccc_trend(samples, now=now) == CCCTrend.IMPROVING


def test_ccc_trend_only_in_window():
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    # 6 samples in window + 5 way outside
    in_window = [_ccc(0.6, i, base=now) for i in range(6)]
    out_of_window = [_ccc(0.1, 60 + i, base=now) for i in range(5)]
    assert derive_ccc_trend(
        in_window + out_of_window, now=now, window_days=30
    ) == CCCTrend.STABLE


# --------------------------------------------------------------------------
# PACEConsentAnnotation
# --------------------------------------------------------------------------


def test_consent_annotation_links_to_acap_record_by_id():
    plan = ModalityPlan(
        primary_channel=PrimaryChannel.VOICE,
        language="en",
    )
    ann = PACEConsentAnnotation(
        annotation_id="ann-1",
        consent_record_id="acap-rec-42",  # references ACAP, doesn't mutate it
        principal_id="p-1",
        pcp_version="1.0",
        ccc_performed=False,
        interaction_modality=plan,
        annotated_at="2026-04-30T10:00:00Z",
    )
    blob = ann.model_dump_json()
    parsed = PACEConsentAnnotation.model_validate_json(blob)
    assert parsed.consent_record_id == "acap-rec-42"


def test_consent_annotation_ccc_performed_requires_ccc_fields():
    plan = ModalityPlan(primary_channel=PrimaryChannel.VOICE, language="en")
    with pytest.raises(ValueError, match="ccc_performed=True"):
        PACEConsentAnnotation(
            annotation_id="ann-1",
            consent_record_id="acap-rec-42",
            principal_id="p-1",
            pcp_version="1.0",
            ccc_performed=True,  # but the CCC fields are absent
            interaction_modality=plan,
            annotated_at="2026-04-30T10:00:00Z",
        )


def test_consent_annotation_active_assessment_requires_challenge():
    plan = ModalityPlan(primary_channel=PrimaryChannel.VOICE, language="en")
    with pytest.raises(ValueError, match="active_challenge"):
        PACEConsentAnnotation(
            annotation_id="ann-1",
            consent_record_id="acap-rec-42",
            principal_id="p-1",
            pcp_version="1.0",
            ccc_performed=True,
            ccc_capacity_signal=0.8,
            ccc_recommendation=CapacityRecommendation.PROCEED,
            ccc_assessment_method=AssessmentMethod.ACTIVE,
            # active_challenge missing
            interaction_modality=plan,
            annotated_at="2026-04-30T10:00:00Z",
        )


def test_consent_annotation_skipped_ccc_rejects_partial_fields():
    """ccc_performed=False but ccc_recommendation set is internally inconsistent."""
    plan = ModalityPlan(primary_channel=PrimaryChannel.VOICE, language="en")
    with pytest.raises(ValueError, match="ccc_performed=False"):
        PACEConsentAnnotation(
            annotation_id="ann-1",
            consent_record_id="acap-rec-42",
            principal_id="p-1",
            pcp_version="1.0",
            ccc_performed=False,
            ccc_recommendation=CapacityRecommendation.PROCEED,  # incoherent
            interaction_modality=plan,
            annotated_at="2026-04-30T10:00:00Z",
        )


# --------------------------------------------------------------------------
# PACEViolationNotice
# --------------------------------------------------------------------------


def test_violation_notice_round_trip():
    digest = PACEViolationNotice.compute_evidence_hash(
        principal_id="p-1",
        aic_version="2.0",
        offending_agent_id="did:agent:rogue",
        violation_type=ViolationType.TIME_WINDOW,
        detected_at="2026-04-30T22:30:00Z",
        clause_id="aic.time_windows[0]",
    )
    notice = PACEViolationNotice(
        notice_id="n-1",
        principal_id="p-1",
        aic_version="2.0",
        offending_agent_id="did:agent:rogue",
        violation_type=ViolationType.TIME_WINDOW,
        detected_at="2026-04-30T22:30:00Z",
        detected_by="did:orch:home",
        enforcement_actions=[
            EnforcementAction.BLOCK_AGENT,
            EnforcementAction.NOTIFY_GUARDIAN,
        ],
        block_duration_seconds=86400,
        evidence_hash=digest,
    )
    blob = notice.model_dump_json()
    parsed = PACEViolationNotice.model_validate_json(blob)
    assert parsed.evidence_hash == digest


def test_violation_notice_requires_at_least_one_action():
    with pytest.raises(ValueError):
        PACEViolationNotice(
            notice_id="n-1",
            principal_id="p-1",
            aic_version="2.0",
            offending_agent_id="did:agent:rogue",
            violation_type=ViolationType.TIME_WINDOW,
            detected_at="2026-04-30T22:30:00Z",
            detected_by="did:orch:home",
            enforcement_actions=[],
            block_duration_seconds=3600,
            evidence_hash="sha256:" + "0" * 64,
        )


def test_evidence_hash_helper_is_deterministic():
    args = dict(
        principal_id="p-1",
        aic_version="2.0",
        offending_agent_id="did:agent:rogue",
        violation_type=ViolationType.OPTION_OVERLOAD,
        detected_at="2026-04-30T22:30:00Z",
        clause_id="aic.max_options_per_turn",
    )
    a = PACEViolationNotice.compute_evidence_hash(**args)
    b = PACEViolationNotice.compute_evidence_hash(**args)
    assert a == b
    assert a.startswith("sha256:")
    assert len(a) == len("sha256:") + 64
