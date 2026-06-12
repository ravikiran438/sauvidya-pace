# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the PACE AG-UI binding (Governance over AG-UI)."""

from __future__ import annotations

import pytest

from pace.ag_ui import (
    GOVERNANCE_KEY,
    active_challenge_interrupt,
    envelope_state_snapshot,
    resolve_active_challenge,
)
from pace.types.accessibility_service_ref import (
    PACE_EXTENSION_URI,
    AccessibilityServiceRef,
)
from pace.types.active_challenge import (
    ActiveChallenge,
    ChallengeType,
    ResponseClassification,
)


def _ref() -> AccessibilityServiceRef:
    return AccessibilityServiceRef(
        version="1.0.0",
        pcp_endpoint="https://orch.example.com/pace/pcp",
        aic_endpoint="https://orch.example.com/pace/aic/{principal_id}",
        violation_notice_endpoint="https://orch.example.com/pace/violations",
        supported_modalities=["voice", "large_text"],
        supported_languages=["en", "te"],
    )


def _interrupt(window=300_000, posed="2026-04-01T10:00:00Z"):
    ev = active_challenge_interrupt(
        challenge_id="ch-1",
        challenge_type=ChallengeType.CONFIRMATION_REPEAT,
        challenge_text="Repeat back the amount you are approving.",
        response_window_ms=window,
        posed_at=posed,
    )
    return ev["outcome"]["interrupts"][0]


# --- envelope state snapshot -------------------------------------------------

def test_envelope_snapshot_keyed_by_pace_uri():
    ev = envelope_state_snapshot(_ref())
    assert ev["type"] == "STATE_SNAPSHOT"
    assert PACE_EXTENSION_URI in ev["snapshot"]  # B-1: identity by URI
    assert ev["snapshot"][PACE_EXTENSION_URI]["supported_modalities"] == ["voice", "large_text"]


# --- interrupt construction --------------------------------------------------

def test_interrupt_shape_and_identity():
    ev = active_challenge_interrupt(
        challenge_id="ch-1",
        challenge_type="comprehension_question",
        challenge_text="What did you just agree to?",
        response_window_ms=300_000,
        posed_at="2026-04-01T10:00:00Z",
    )
    assert ev["type"] == "RUN_FINISHED"
    assert ev["outcome"]["type"] == "interrupt"
    it = ev["outcome"]["interrupts"][0]
    assert it["reason"] == "input_required"
    assert it["message"] == "What did you just agree to?"
    assert "responseSchema" in it
    gov = it["metadata"][GOVERNANCE_KEY]
    assert gov["uri"] == PACE_EXTENSION_URI            # B-1
    assert gov["type"] == "ActiveChallenge"
    # challenge_hash binds the interrupt to the exact text shown
    assert gov["challenge_hash"] == ActiveChallenge.hash_canonical_text(
        "What did you just agree to?"
    )


def test_interrupt_expires_at_equals_window():
    it = _interrupt(window=300_000, posed="2026-04-01T10:00:00Z")
    assert it["expiresAt"] == "2026-04-01T10:05:00Z"  # +300_000 ms = +5 min


def test_interrupt_rejects_nonpositive_window():
    with pytest.raises(ValueError):
        active_challenge_interrupt(
            challenge_id="ch-1",
            challenge_type=ChallengeType.EQUIVALENCE_CHECK,
            challenge_text="x",
            response_window_ms=0,
            posed_at="2026-04-01T10:00:00Z",
        )


# --- resume resolution (B-3 typed resume) ------------------------------------

def test_resolve_resolved_roundtrips_to_valid_challenge():
    it = _interrupt()
    resume = {"interruptId": it["id"], "status": "resolved",
              "payload": {"response_text": "forty two dollars"}}
    ac = resolve_active_challenge(
        interrupt=it, resume=resume,
        classified_as=ResponseClassification.COMPREHENDED,
        response_received_ms=4200,
    )
    assert isinstance(ac, ActiveChallenge)
    assert ac.challenge_id == "ch-1"
    assert ac.challenge_hash == it["metadata"][GOVERNANCE_KEY]["challenge_hash"]
    assert ac.response_hash == ActiveChallenge.hash_canonical_text("forty two dollars")
    assert ac.classified_as == ResponseClassification.COMPREHENDED
    assert ac.response_received_ms == 4200


def test_resolve_cancelled_is_non_responsive():
    it = _interrupt()
    ac = resolve_active_challenge(
        interrupt=it, resume={"interruptId": it["id"], "status": "cancelled"},
    )
    assert ac.classified_as == ResponseClassification.NON_RESPONSIVE
    assert ac.response_received_ms is None
    # absence is the empty-string hash, distinguishable from refusal
    assert ac.response_hash == ActiveChallenge.hash_canonical_text("")


def test_resolve_refused_in_payload_not_status():
    it = _interrupt()
    resume = {"interruptId": it["id"], "status": "resolved",
              "payload": {"refused": True}}
    ac = resolve_active_challenge(
        interrupt=it, resume=resume,
        classified_as=ResponseClassification.REFUSED,
        response_received_ms=1500,
    )
    assert ac.classified_as == ResponseClassification.REFUSED
    assert ac.response_received_ms == 1500              # refusal still has timing
    assert ac.response_hash == ActiveChallenge.hash_canonical_text("")


def test_resolve_rejects_foreign_interrupt():
    foreign = {"id": "x", "reason": "confirmation",
               "metadata": {GOVERNANCE_KEY: {"uri": "https://example.com/other/v1"}}}
    with pytest.raises(ValueError):
        resolve_active_challenge(
            interrupt=foreign, resume={"interruptId": "x", "status": "cancelled"})


def test_resolve_resolved_requires_classification():
    it = _interrupt()
    with pytest.raises(ValueError):
        resolve_active_challenge(
            interrupt=it,
            resume={"interruptId": it["id"], "status": "resolved",
                    "payload": {"response_text": "ok"}},
        )
