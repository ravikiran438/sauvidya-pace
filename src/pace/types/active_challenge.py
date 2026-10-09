# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Active assessment evidence for ConsentCapacityCheck.

The PACE preprint distinguishes ``passive`` (interpolated from interaction
signals) from ``active`` (the orchestrator presented an explicit
challenge and the principal responded) capacity assessment. Until this
module existed, "active" was only a label on ``AssessmentMethod``; nothing
in the protocol let an auditor verify that an active assessment actually
occurred.

This module pins the wire shape of an ActiveChallenge: a tamper-evident
record of a challenge-response interaction. Neither the challenge text nor
the principal's raw response is stored, only keyed digests of their
canonical forms, plus timing and a coarse classification.

Why keyed: responses to a capacity check are short and guessable ("yes",
"the insurance", "Tuesday"). A plain SHA-256 of such a response can be
recovered by hashing likely answers, without ever seeing the transcript.
Digests are therefore HMAC-SHA256 under an audit key that the principal's
PACE orchestrator holds on-device (CCC-2). Without the key, a digest
cannot be dictionary-guessed. A local auditor holding the key and the
transcript can still recompute and verify it. Both digests also cover
``challenge_id`` and a label naming their role, so a digest cannot be
moved to another record or swapped between challenge and response.
``digest_key_id`` names the key so it can be rotated.
"""

from __future__ import annotations

import hashlib
import hmac
import unicodedata
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


MIN_AUDIT_KEY_BYTES = 32
_CHALLENGE_LABEL = b"pace.active-challenge.challenge.v1"
_RESPONSE_LABEL = b"pace.active-challenge.response.v1"


class ChallengeType(str, Enum):
    """Categories of active challenges. Extensible.

    Implementations SHOULD pick the type that most accurately describes
    the interaction so audit trails remain interpretable.
    """

    # Asks the principal to paraphrase the action just consented to.
    COMPREHENSION_QUESTION = "comprehension_question"

    # Asks the principal to repeat back a key fact (amount, recipient,
    # appointment time) before completing.
    CONFIRMATION_REPEAT = "confirmation_repeat"

    # Tests whether the principal recalls context from earlier in the
    # same session (e.g. "what did we just decide about X?").
    CONTEXT_CONTINUITY = "context_continuity"

    # Presents two semantically equivalent options and asks the
    # principal to identify them as equivalent. Detects rote-yes drift.
    EQUIVALENCE_CHECK = "equivalence_check"


class ResponseClassification(str, Enum):
    """How the orchestrator graded the principal's response."""

    COMPREHENDED = "comprehended"
    PARTIAL = "partial"
    NON_RESPONSIVE = "non_responsive"
    REFUSED = "refused"


class ActiveChallenge(BaseModel):
    """Tamper-evident record of one active CCC challenge-response.

    Linked into ConsentCapacityCheck via challenge_id. The keyed digests
    (challenge_hash, response_hash) let an auditor who holds the audit
    key and the transcript confirm what was asked and answered, and
    reveal nothing to anyone without the key.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    challenge_id: str = Field(..., description="UUID v4")
    challenge_type: ChallengeType
    digest_key_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Identifier of the on-device audit key used for both digests. "
            "Lets the orchestrator rotate keys while old records stay "
            "verifiable."
        ),
    )
    challenge_hash: str = Field(
        ...,
        pattern=r"^hmac-sha256:[0-9a-f]{64}$",
        description=(
            "HMAC-SHA256 under the audit key over the challenge label, "
            "``challenge_id`` and the canonical challenge text, formatted "
            "``hmac-sha256:<hex>``. Canonical form: NFC-normalized, leading "
            "and trailing whitespace stripped, UTF-8 encoded. See "
            "``challenge_digest``."
        ),
    )
    response_hash: str = Field(
        ...,
        pattern=r"^hmac-sha256:[0-9a-f]{64}$",
        description=(
            "HMAC-SHA256 under the same key over the response label, "
            "``challenge_id`` and the principal's canonical response, "
            "formatted ``hmac-sha256:<hex>``. Bound to ``challenge_id`` so it "
            "cannot be copied into another record. An empty or refused "
            "response is the digest of the empty string; ``classified_as`` "
            "distinguishes refusal from absence. See ``response_digest``."
        ),
    )
    response_window_ms: int = Field(
        ..., gt=0,
        description="Maximum allowed response time in milliseconds.",
    )
    response_received_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description=(
            "Actual elapsed milliseconds between challenge presentation "
            "and response receipt. None when classified NON_RESPONSIVE."
        ),
    )
    classified_as: ResponseClassification
    posed_at: str = Field(..., description="ISO 8601 UTC of presentation")

    @model_validator(mode="after")
    def _coherent_classification(self) -> "ActiveChallenge":
        if (
            self.classified_as == ResponseClassification.NON_RESPONSIVE
            and self.response_received_ms is not None
        ):
            raise ValueError(
                "NON_RESPONSIVE requires response_received_ms to be None"
            )
        if (
            self.classified_as != ResponseClassification.NON_RESPONSIVE
            and self.response_received_ms is None
        ):
            raise ValueError(
                "Non-NON_RESPONSIVE classification requires response_received_ms"
            )
        if (
            self.response_received_ms is not None
            and self.response_received_ms > self.response_window_ms
        ):
            raise ValueError(
                "response_received_ms cannot exceed response_window_ms"
            )
        return self

    @staticmethod
    def canonical_text(text: str) -> str:
        """NFC-normalize and strip, so every party digests the same bytes."""
        return unicodedata.normalize("NFC", text).strip()

    @classmethod
    def challenge_digest(cls, challenge_id: str, text: str, audit_key: bytes) -> str:
        """Keyed digest for ``challenge_hash``, bound to ``challenge_id``."""
        return cls._digest(_CHALLENGE_LABEL, challenge_id, text, audit_key)

    @classmethod
    def response_digest(cls, challenge_id: str, text: str, audit_key: bytes) -> str:
        """Keyed digest for ``response_hash``, bound to ``challenge_id``.

        Two records where the principal said "yes" get different digests,
        so a response digest cannot be copied into another record.
        """
        return cls._digest(_RESPONSE_LABEL, challenge_id, text, audit_key)

    @classmethod
    def matches_challenge(
        cls, challenge_id: str, text: str, audit_key: bytes, digest: str
    ) -> bool:
        """Constant-time check of a ``challenge_hash``."""
        return hmac.compare_digest(
            cls.challenge_digest(challenge_id, text, audit_key), digest
        )

    @classmethod
    def matches_response(
        cls, challenge_id: str, text: str, audit_key: bytes, digest: str
    ) -> bool:
        """Constant-time check of a ``response_hash``."""
        return hmac.compare_digest(
            cls.response_digest(challenge_id, text, audit_key), digest
        )

    @classmethod
    def _digest(
        cls, label: bytes, challenge_id: str, text: str, audit_key: bytes
    ) -> str:
        """HMAC-SHA256 over ``label || 0x00 || challenge_id || 0x00 || text``.

        ``audit_key`` is the orchestrator's on-device secret, at least 32
        bytes. It MUST NOT leave the device. The label separates challenge
        digests from response digests; ``challenge_id`` binds both to one
        record. ``challenge_id`` may not contain NUL, so the encoding is
        unambiguous.
        """
        if len(audit_key) < MIN_AUDIT_KEY_BYTES:
            raise ValueError(
                f"audit_key must be at least {MIN_AUDIT_KEY_BYTES} bytes"
            )
        if not challenge_id or "\x00" in challenge_id:
            raise ValueError("challenge_id must be non-empty and contain no NUL")
        message = b"\x00".join(
            (
                label,
                challenge_id.encode("utf-8"),
                cls.canonical_text(text).encode("utf-8"),
            )
        )
        mac = hmac.new(audit_key, message, hashlib.sha256)
        return f"hmac-sha256:{mac.hexdigest()}"
