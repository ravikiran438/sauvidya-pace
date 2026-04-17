# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""IM-Precondition and IM-2 (language match) validators."""

from __future__ import annotations

from pace.types.interaction_modality import InteractionModality
from pace.types.principal_capability_profile import PrincipalCapabilityProfile


class ModalityPreconditionError(ValueError):
    """IM-1: Agent attempted interaction without computing InteractionModality."""


class LanguageMismatchError(ValueError):
    """IM-2: Agent defaulted to a language not in the principal's PCP."""


def validate_im_precondition(
    modality: InteractionModality | None,
    pcp: PrincipalCapabilityProfile,
) -> None:
    """IM-1: An agent MUST compute an InteractionModality from the PCP
    before initiating any interaction."""
    if modality is None:
        raise ModalityPreconditionError(
            f"IM-1 violated: no InteractionModality computed for principal "
            f"{pcp.principal_id!r} (PCP version {pcp.version})"
        )
    if modality.pcp_version != pcp.version:
        raise ModalityPreconditionError(
            f"IM-1 violated: InteractionModality references PCP version "
            f"{modality.pcp_version!r} but current PCP is {pcp.version!r}"
        )


def validate_language_match(
    modality: InteractionModality,
    pcp: PrincipalCapabilityProfile,
) -> None:
    """IM-2: The modality's language MUST be one the principal speaks.
    MUST NOT default to English if the principal's PCP does not list it
    at sufficient fluency."""
    pcp_languages = {lf.code for lf in pcp.language}
    if modality.modality_plan.language not in pcp_languages:
        raise LanguageMismatchError(
            f"IM-2 violated: modality language {modality.modality_plan.language!r} "
            f"is not in principal's declared languages {pcp_languages!r}. "
            "Agent MUST NOT default to a language the principal does not speak."
        )
