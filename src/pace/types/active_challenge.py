# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Active assessment evidence for ConsentCapacityCheck.

The PACE preprint distinguishes ``passive`` (interpolated from interaction
signals) from ``active`` (the orchestrator presented an explicit
challenge and the principal responded) capacity assessment. Until this
module existed, "active" was only a label on ``AssessmentMethod``; nothing
in the protocol let a third-party auditor verify that an active
assessment actually occurred.

This module pins the wire shape of an ActiveChallenge: a tamper-evident
record of a challenge-response interaction. Importantly, neither the
challenge text nor the principal's raw response is stored; only their
canonical SHA-256 digests, plus timing and a coarse classification.

This satisfies CCC-2 (results MUST NOT be transmitted to remote agents)
because the digests reveal nothing about the principal's mental state
to any party who does not already hold the original text. The orchestrator
holds the original; auditors only ever see hashes.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    Linked into ConsentCapacityCheck via challenge_id. The digests
    (challenge_hash, response_hash) let an auditor confirm the
    challenge happened and the response was non-empty without
    revealing content.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    challenge_id: str = Field(..., description="UUID v4")
    challenge_type: ChallengeType
    challenge_hash: str = Field(
        ...,
        description=(
            "SHA-256 of the canonical challenge text, formatted "
            "``sha256:<hex>``. Canonical form: NFC-normalized UTF-8, "
            "trailing whitespace stripped, locale-independent."
        ),
    )
    response_hash: str = Field(
        ...,
        description=(
            "SHA-256 of the principal's canonical response, formatted "
            "``sha256:<hex>``. Empty response is encoded as the SHA-256 of "
            "the empty string (e3b0c44...) so absence is distinguishable "
            "from refusal."
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

    @classmethod
    def hash_canonical_text(cls, text: str) -> str:
        """Compute the canonical SHA-256 digest used for both hashes.

        Canonical form: Unicode NFC normalization, UTF-8 encoding, then
        SHA-256. Surfaced so the orchestrator and the auditor compute
        the same value over a shared transcript.
        """
        import unicodedata

        normalized = unicodedata.normalize("NFC", text).strip()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"
