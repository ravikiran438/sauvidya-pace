# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AG-UI binding for PACE.

AG-UI (the Agent-User Interaction protocol) is the agent <-> human-app
transport, alongside A2A (agent <-> agent) and MCP (agent <-> tools). PACE
governs whether the human can perceive, comprehend, and respond, so AG-UI is
PACE's natural transport. This module carries the PACE data plane over AG-UI
under the cross-cutting "Governance over AG-UI" convention:

  * The capability envelope (``AccessibilityServiceRef``) is published as an
    AG-UI ``STATE_SNAPSHOT`` keyed by ``PACE_EXTENSION_URI`` (the same URI used
    on the A2A AgentCard and in MCP ``_meta``).
  * An active ConsentCapacityCheck (``ActiveChallenge``) is presented as an
    AG-UI **interrupt** (``reason: "input_required"``); the principal's resume
    payload is turned back into a typed, validated ``ActiveChallenge``.

The binding is dependency-free: it builds plain JSON-serializable AG-UI event
dicts. Identity is carried in ``metadata.governance.uri`` so a governance-aware
client routes the interrupt, while a generic AG-UI client falls back to
``message`` + ``responseSchema`` and still works (invariant B-2, non-breaking).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pace.types.accessibility_service_ref import (
    PACE_EXTENSION_URI,
    AccessibilityServiceRef,
)
from pace.types.active_challenge import (
    ActiveChallenge,
    ChallengeType,
    ResponseClassification,
)

# Key under an interrupt's ``metadata`` that carries protocol identity.
GOVERNANCE_KEY = "governance"

# JSON Schema for the resume payload of a PACE ActiveChallenge interrupt.
# A denial is encoded as ``refused: true`` *inside* the payload (invariant
# B-3) — never as AG-UI ``status: "cancelled"`` (which means abandoned).
CHALLENGE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "response_text": {
            "type": "string",
            "description": "The principal's response to the challenge.",
        },
        "refused": {
            "type": "boolean",
            "description": "True if the principal explicitly refused to respond.",
        },
    },
    "additionalProperties": False,
}


def _parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def envelope_state_snapshot(ref: AccessibilityServiceRef) -> dict[str, Any]:
    """AG-UI ``STATE_SNAPSHOT`` publishing the PACE capability envelope.

    Emit this at run start, before any interrupt (invariant B-5), so the
    frontend can adapt modality/timing and so a resume can rebuild context.
    """
    return {
        "type": "STATE_SNAPSHOT",
        "snapshot": {PACE_EXTENSION_URI: ref.model_dump()},
    }


def active_challenge_interrupt(
    *,
    challenge_id: str,
    challenge_type: ChallengeType | str,
    challenge_text: str,
    response_window_ms: int,
    posed_at: str,
) -> dict[str, Any]:
    """Build a ``RUN_FINISHED`` interrupt presenting an ActiveChallenge.

    The challenge text is shown to the principal (``message``) and bound to the
    interrupt by its canonical hash (in ``metadata.governance``), so the typed
    ``ActiveChallenge`` produced on resume is tamper-evidently linked to what
    was actually asked. ``expiresAt`` enforces ``response_window_ms``.
    """
    if response_window_ms <= 0:
        raise ValueError("response_window_ms must be positive")
    ctype = ChallengeType(challenge_type)
    challenge_hash = ActiveChallenge.hash_canonical_text(challenge_text)
    expires_at = _iso(_parse_iso(posed_at) + timedelta(milliseconds=response_window_ms))
    interrupt = {
        "id": f"pace-cc-{challenge_id}",
        "reason": "input_required",
        "message": challenge_text,
        "responseSchema": CHALLENGE_RESPONSE_SCHEMA,
        "expiresAt": expires_at,
        "metadata": {
            GOVERNANCE_KEY: {
                "uri": PACE_EXTENSION_URI,
                "type": "ActiveChallenge",
                "challenge_id": challenge_id,
                "challenge_type": ctype.value,
                "challenge_hash": challenge_hash,
                "response_window_ms": response_window_ms,
                "posed_at": posed_at,
            }
        },
    }
    return {
        "type": "RUN_FINISHED",
        "outcome": {"type": "interrupt", "interrupts": [interrupt]},
    }


def resolve_active_challenge(
    *,
    interrupt: dict[str, Any],
    resume: dict[str, Any],
    classified_as: ResponseClassification | str | None = None,
    response_received_ms: Optional[int] = None,
) -> ActiveChallenge:
    """Turn an AG-UI resume into a typed, validated ``ActiveChallenge``.

    The orchestrator supplies the grade (``classified_as``) and elapsed timing
    for a resolved response — comprehension grading is a PACE decision, not a
    wire concern. A ``status: "cancelled"`` resume is recorded as
    ``NON_RESPONSIVE`` regardless. Raises ``ValueError`` if the interrupt is not
    a PACE ActiveChallenge (invariant B-1).
    """
    gov = (interrupt.get("metadata") or {}).get(GOVERNANCE_KEY) or {}
    if gov.get("uri") != PACE_EXTENSION_URI or gov.get("type") != "ActiveChallenge":
        raise ValueError("interrupt is not a PACE ActiveChallenge")

    status = resume.get("status")
    payload = resume.get("payload") or {}

    if status == "cancelled":
        response_text = ""
        classified = ResponseClassification.NON_RESPONSIVE
        elapsed: Optional[int] = None
    elif status == "resolved":
        if classified_as is None:
            raise ValueError("classified_as is required for a resolved challenge")
        classified = ResponseClassification(classified_as)
        if classified == ResponseClassification.NON_RESPONSIVE:
            response_text, elapsed = "", None
        else:
            # Denial is encoded in the payload, not the status (B-3).
            response_text = "" if payload.get("refused") else payload.get("response_text", "")
            elapsed = response_received_ms
    else:
        raise ValueError(f"unknown resume status {status!r}")

    return ActiveChallenge(
        challenge_id=gov["challenge_id"],
        challenge_type=ChallengeType(gov["challenge_type"]),
        challenge_hash=gov["challenge_hash"],
        response_hash=ActiveChallenge.hash_canonical_text(response_text),
        response_window_ms=gov["response_window_ms"],
        response_received_ms=elapsed,
        classified_as=classified,
        posed_at=gov["posed_at"],
    )
