# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""PACEViolationNotice: cross-orchestrator broadcast for AIC violations.

The PACE preprint declares ``violation_policy`` (e.g. "block_agent +
notify_guardian") but does not specify how a block propagates from the
detecting orchestrator to peer orchestrators that may also be talking to
the offending agent on behalf of the same principal. Without a
broadcast schema the policy degrades to a local-only mute and the
principal can be re-victimized through a different orchestrator.

This module pins the on-wire schema of a PACEViolationNotice and the
required handling rules.

## Wire format

POST to each peer orchestrator's ``violation_notice_endpoint`` (declared
in ``AccessibilityServiceRef``) with a JSON body matching this model.
The body MUST be signed by the issuing orchestrator's key (envelope
field: ``issuer_signature``) so receivers can authenticate origin.

## Handling rules (V-1, V-2, V-3)

  V-1: A receiving orchestrator that is itself bound by the same
       ``aic_version`` for the same ``principal_id`` MUST add the
       ``offending_agent_id`` to its local block list for at least
       ``block_duration_seconds`` from ``detected_at``.

  V-2: The receiving orchestrator MUST NOT forward the notice; the
       broadcast is one-hop. Hop-count protections in the protocol
       prevent loops without relying on receiver discipline.

  V-3: A receiver that has no AIC for ``principal_id`` MUST log the
       notice for audit but MUST NOT apply the block, since the
       principal is not under its care.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ViolationType(str, Enum):
    """Which AIC clause was breached. Mirrors ViolationPolicy keys."""

    TIME_WINDOW = "time_window"
    OPTION_OVERLOAD = "option_overload"
    LANGUAGE_MISMATCH = "language_mismatch"
    CAPACITY_CHECK_SKIP = "capacity_check_skip"


class EnforcementAction(str, Enum):
    """The action the issuing orchestrator applied locally and is asking
    peers to mirror.

    Names align with the strings used in ``ViolationPolicy`` defaults
    (``"block_agent + notify_guardian"`` etc.) but split into structured
    enum values so peers can apply enforcement without parsing.
    """

    BLOCK_AGENT = "block_agent"
    REJECT_INTERACTION = "reject_interaction"
    NOTIFY_GUARDIAN = "notify_guardian"
    AUDIT_FLAG = "audit_flag"
    ESCALATE = "escalate"


class PACEViolationNotice(BaseModel):
    """One-hop broadcast that an AIC violation has occurred.

    Issued by the detecting orchestrator; consumed by peer
    orchestrators bound by the same AIC for the same principal. Per
    CCC-2, the notice MUST NOT carry principal speech, response text,
    or any capacity_signal value; only structured facts and digests.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    notice_id: str = Field(..., description="UUID v4")
    principal_id: str = Field(
        ...,
        description=(
            "The principal under whose AIC this violation occurred. "
            "Receivers use this to scope the block to peers of this "
            "principal only (V-3)."
        ),
    )
    aic_version: str = Field(
        ...,
        description=(
            "AdaptiveInteractionContract version that was breached. "
            "Receivers MUST be on the same version (V-1) before applying "
            "enforcement; older/newer AICs imply a different rule set."
        ),
    )
    offending_agent_id: str = Field(
        ...,
        description=(
            "DID or HTTPS URL of the agent that breached the AIC. The "
            "block is scoped to this agent."
        ),
    )
    violation_type: ViolationType
    detected_at: str = Field(..., description="ISO 8601 UTC")
    detected_by: str = Field(
        ...,
        description=(
            "Identifier (DID or URL) of the issuing orchestrator. Pairs "
            "with issuer_signature for authentication."
        ),
    )
    enforcement_actions: list[EnforcementAction] = Field(
        ...,
        min_length=1,
        description=(
            "The actions the issuer applied locally; receivers SHOULD "
            "mirror those that are within their authority."
        ),
    )
    block_duration_seconds: int = Field(
        ...,
        gt=0,
        description=(
            "How long the block applies, measured from detected_at. "
            "Receivers MUST honour at least this duration."
        ),
    )
    evidence_hash: str = Field(
        ...,
        description=(
            "SHA-256 over a canonical, principal-data-free description of "
            "the violation (timestamps, AIC clause id, agent id, "
            "violation_type). Format: ``sha256:<hex>``. Lets auditors "
            "tie the notice to a stored evidence record without exposing "
            "principal content on the wire."
        ),
    )
    issuer_signature: Optional[str] = Field(
        default=None,
        description=(
            "JWS (compact serialization) over the canonical JSON of this "
            "notice (excluding this field), signed by the issuing "
            "orchestrator's key. RECOMMENDED."
        ),
    )

    @staticmethod
    def compute_evidence_hash(
        *,
        principal_id: str,
        aic_version: str,
        offending_agent_id: str,
        violation_type: ViolationType,
        detected_at: str,
        clause_id: str,
    ) -> str:
        """Canonical evidence digest helper.

        Issuers SHOULD use this to compute ``evidence_hash`` so audit
        records keyed by the same digest are reproducible.
        """
        canonical = (
            f"{principal_id}|{aic_version}|{offending_agent_id}|"
            f"{violation_type.value}|{detected_at}|{clause_id}"
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"
