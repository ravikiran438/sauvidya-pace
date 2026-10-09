# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""IM-Precondition and IM-2 (language match) validators."""

from __future__ import annotations

from pace.types.adaptive_interaction_contract import AdaptiveInteractionContract
from pace.types.interaction_modality import InteractionModality
from pace.types.principal_capability_profile import PrincipalCapabilityProfile

DEFAULT_MIN_LANGUAGE_FLUENCY = 0.7
_LANGUAGE_PIN = "language:"


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


def acceptable_languages(
    pcp: PrincipalCapabilityProfile,
    min_fluency: float = DEFAULT_MIN_LANGUAGE_FLUENCY,
) -> set[str]:
    """Languages an agent may use with this principal (IM-2).

    A pin in ``adaptations_required`` (``language:te``) wins: only pinned
    languages are acceptable. Without a pin, a language must be listed in
    the PCP with fluency at or above ``min_fluency``.
    """
    pinned = {
        a[len(_LANGUAGE_PIN):].strip()
        for a in pcp.adaptations_required
        if a.startswith(_LANGUAGE_PIN) and a[len(_LANGUAGE_PIN):].strip()
    }
    if pinned:
        return pinned
    return {lf.code for lf in pcp.language if lf.fluency >= min_fluency}


def _floor(contract: AdaptiveInteractionContract | None) -> float:
    if contract is None:
        return DEFAULT_MIN_LANGUAGE_FLUENCY
    return contract.interaction_rules.min_language_fluency


def _why(pcp: PrincipalCapabilityProfile, language: str, floor: float) -> str:
    pins = [a for a in pcp.adaptations_required if a.startswith(_LANGUAGE_PIN)]
    if pins:
        return f"the PCP pins {', '.join(sorted(pins))}"
    listed = {lf.code: lf.fluency for lf in pcp.language}
    if language in listed:
        return (
            f"fluency in {language!r} is {listed[language]:.2f}, below the "
            f"floor of {floor:.2f}"
        )
    return f"{language!r} is not among the principal's declared languages"


def validate_language_match(
    modality: InteractionModality,
    pcp: PrincipalCapabilityProfile,
    contract: AdaptiveInteractionContract | None = None,
) -> None:
    """IM-2: the agent MUST use a language the principal can follow.

    A pinned language (``language:<code>`` in ``adaptations_required``)
    is the only acceptable one. Otherwise the language must be listed at
    or above ``contract.interaction_rules.min_language_fluency`` (0.7 when
    no contract is given). An agent that cannot comply MUST NOT fall back
    to another language: it routes to a sub-agent that speaks an
    acceptable language, or escalates to ``modality.escalation_target``.
    """
    floor = _floor(contract)
    language = modality.modality_plan.language
    allowed = acceptable_languages(pcp, floor)
    if language in allowed:
        return
    escalate_to = modality.escalation_target or "the guardian"
    if not allowed:
        raise LanguageMismatchError(
            f"IM-2 violated: no language in PCP {pcp.version!r} for "
            f"{pcp.principal_id!r} meets the fluency floor of {floor:.2f}. "
            f"Escalate to {escalate_to}; do not interact."
        )
    raise LanguageMismatchError(
        f"IM-2 violated: modality language {language!r} is not acceptable "
        f"for {pcp.principal_id!r} because {_why(pcp, language, floor)}. "
        f"Route to a sub-agent that speaks one of {sorted(allowed)!r}, "
        f"otherwise escalate to {escalate_to}. Do not fall back to "
        f"{language!r}."
    )


def validate_contract_language(
    contract: AdaptiveInteractionContract,
    pcp: PrincipalCapabilityProfile,
) -> None:
    """IM-2 applied to the contract: an AIC MUST NOT bind every agent to a
    language the PCP rules out. Catches a guardian approving, by mistake or
    otherwise, an English contract for a principal who thinks in Telugu.
    """
    floor = _floor(contract)
    language = contract.interaction_rules.language
    allowed = acceptable_languages(pcp, floor)
    if language not in allowed:
        raise LanguageMismatchError(
            f"IM-2 violated: AIC for {contract.principal_id!r} binds "
            f"language {language!r}, but {_why(pcp, language, floor)}; "
            f"acceptable languages are {sorted(allowed)!r}"
        )
