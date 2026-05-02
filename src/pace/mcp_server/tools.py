# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tool registrations for the PACE MCP server.

Each tool wraps a PACE invariant validator: six from PACE Core (the
named accessibility invariants) and four from the augmentation_profile
extension (AUG-1, AUG-3, AUG-4, AUG-5). Failures return
``{"ok": false, "error": ...}`` with the validator's own diagnostic
message.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from pace.types import (
    AccessibilityServiceRef,
    ActiveChallenge,
    AdaptiveInteractionContract,
    CCCTrend,
    ConsentCapacityCheck,
    InteractionModality,
    PACEConsentAnnotation,
    PACEViolationNotice,
    PrincipalCapabilityProfile,
    derive_ccc_trend,
)
from pace.validators import (
    CCCGateError,
    CCCPrivacyError,
    LanguageMismatchError,
    ModalityPreconditionError,
    OptionOverloadError,
    TimeWindowViolationError,
    validate_ccc_gate,
    validate_ccc_privacy,
    validate_im_precondition,
    validate_language_match,
    validate_option_count,
    validate_time_window,
)

# augmentation_profile extension (AUG-1, AUG-2, AUG-3, AUG-4, AUG-5).
# See extensions/augmentation_profile/.
from pace.extensions.augmentation_profile import (
    AugmentationAction,
    AugmentationError,
    AugmentationProfile,
    AxisRevertedEvent,
    HandoffEvent,
    check_emergency_boundary,
    check_identity_preservation,
    check_reversibility,
    check_skill_maintenance,
)


# ─────────────────────────────────────────────────────────────────────────────
# Generic MCP glue — portable across sibling protocol repos.
# Keep these four symbols (ToolInvocationError, _parse, _ok, _fail) in sync
# by convention when copying to acap, phala, or pratyahara-nerve.
# ─────────────────────────────────────────────────────────────────────────────


class ToolInvocationError(Exception):
    """Raised when a tool's handler rejects its input or runtime fails."""


def _parse(cls, payload: Any, label: str):
    try:
        return cls.model_validate(payload)
    except ValidationError as exc:
        raise ToolInvocationError(f"invalid {label}: {exc}") from exc


def _ok(payload: dict[str, Any]) -> str:
    return json.dumps({"ok": True, **payload}, default=str, indent=2)


def _fail(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Tool handlers (repo-specific; everything below this line is PACE-only).
# ─────────────────────────────────────────────────────────────────────────────


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "validate_principal_capability_profile": {
        "description": (
            "Validate the structural integrity of a "
            "PrincipalCapabilityProfile (PCP). Useful at registration "
            "time when no other operation has caused the PCP to be "
            "validated yet. Other PACE tools validate the PCP "
            "transitively as a side effect."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"pcp": {"type": "object"}},
            "required": ["pcp"],
        },
    },
    "validate_im_precondition": {
        "description": (
            "Verify that an InteractionModality satisfies the "
            "precondition against a PrincipalCapabilityProfile before "
            "use. Pass modality=null to test the 'no modality' path."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "modality": {
                    "type": ["object", "null"],
                    "description": "InteractionModality object, or null.",
                },
                "pcp": {
                    "type": "object",
                    "description": "PrincipalCapabilityProfile object.",
                },
            },
            "required": ["pcp"],
        },
    },
    "validate_language_match": {
        "description": (
            "Verify that an InteractionModality's declared language is "
            "one the principal is fluent in (per the PCP)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "modality": {"type": "object"},
                "pcp": {"type": "object"},
            },
            "required": ["modality", "pcp"],
        },
    },
    "validate_ccc_gate": {
        "description": (
            "Verify that the ConsentCapacityCheck (if any) authorizes "
            "the principal to give consent at this moment. Pass "
            "ccc=null when no check has been performed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "pcp": {"type": "object"},
                "ccc": {
                    "type": ["object", "null"],
                    "description": "ConsentCapacityCheck object, or null.",
                },
            },
            "required": ["pcp"],
        },
    },
    "validate_ccc_privacy": {
        "description": (
            "Verify that only permitted fields of a "
            "ConsentCapacityCheck are transmitted downstream."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ccc": {"type": "object"},
                "transmitted_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Field names actually transmitted.",
                },
            },
            "required": ["ccc", "transmitted_fields"],
        },
    },
    "validate_time_window": {
        "description": (
            "Verify that the current HH:MM time is inside the "
            "contract's allowed interaction window. Emergency "
            "invocations bypass the window."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "contract": {"type": "object"},
                "current_time_hhmm": {
                    "type": "string",
                    "description": "Current time as 'HH:MM' in the "
                    "contract's declared timezone.",
                },
                "is_emergency": {"type": "boolean"},
            },
            "required": ["contract", "current_time_hhmm"],
        },
    },
    "validate_option_count": {
        "description": (
            "Verify that the number of options presented to the "
            "principal does not exceed the contract's cap "
            "(option-overload invariant)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "contract": {"type": "object"},
                "options_presented": {"type": "integer"},
            },
            "required": ["contract", "options_presented"],
        },
    },
    # ── augmentation_profile extension (AUG-1, AUG-3, AUG-4, AUG-5) ────────
    "validate_reversibility": {
        "description": (
            "augmentation_profile AUG-1: verify that an "
            "agent-mediated AugmentationAction was not taken on an axis "
            "that had been reverted by the principal at or before the "
            "action's timestamp."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "object"},
                "reversion_events": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
            "required": ["action", "reversion_events"],
        },
    },
    "validate_identity_preservation": {
        "description": (
            "augmentation_profile AUG-3: verify that any agent action "
            "with alters_identity=true cites explicit identity_consent "
            "on the principal's AugmentationProfile. Implicit consent "
            "is forbidden. Note: AUG-3 enforces against agent "
            "self-attestation; pair with welfare_detectors WD-4 "
            "provenance for end-to-end accountability."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile": {"type": "object"},
                "action": {"type": "object"},
            },
            "required": ["profile", "action"],
        },
    },
    "validate_skill_maintenance": {
        "description": (
            "augmentation_profile AUG-4: verify that no "
            "agent_compensated or agent_amplified action targets an "
            "axis declared 'preserve' on the principal's profile. "
            "Agents MAY scaffold via user_direct actions but MUST NOT "
            "substitute on preserved capacities."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile": {"type": "object"},
                "action": {"type": "object"},
            },
            "required": ["profile", "action"],
        },
    },
    "validate_emergency_boundary": {
        "description": (
            "augmentation_profile AUG-5: verify that no agent-mediated "
            "action was taken between an unacknowledged emergency "
            "HandoffEvent and the human acknowledgement timestamp."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "object"},
                "handoff_events": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
            "required": ["action", "handoff_events"],
        },
    },
    "validate_accessibility_service_ref": {
        "description": (
            "Validate an AccessibilityServiceRef payload (the body of "
            "the AgentCard.capabilities.extensions[] entry whose URI "
            "equals PACE_EXTENSION_URI). Verifies version + the three "
            "endpoints (PCP, AIC, violation_notice) + ≥1 supported "
            "modality and language."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"ref": {"type": "object"}},
            "required": ["ref"],
        },
    },
    "validate_active_challenge": {
        "description": (
            "Validate an ActiveChallenge record (challenge-response "
            "evidence backing assessment_method=ACTIVE on a "
            "ConsentCapacityCheck). Enforces internal coherence: "
            "NON_RESPONSIVE iff response_received_ms is absent; "
            "received_ms ≤ window_ms."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"challenge": {"type": "object"}},
            "required": ["challenge"],
        },
    },
    "validate_pace_consent_annotation": {
        "description": (
            "Validate a PACEConsentAnnotation. Enforces structural "
            "integrity AND referential integrity: when ccc_performed is "
            "true the CCC fields MUST be populated; when "
            "ccc_assessment_method=ACTIVE an active_challenge record "
            "MUST be present."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"annotation": {"type": "object"}},
            "required": ["annotation"],
        },
    },
    "validate_pace_violation_notice": {
        "description": (
            "Validate a PACEViolationNotice and report its handling "
            "policy per V-1/V-2/V-3. Returns the structured fields a "
            "receiving orchestrator needs to apply enforcement: "
            "should_block (V-1 conditions met for the receiver), "
            "block_until (detected_at + block_duration_seconds), and "
            "forwarding_allowed (always false per V-2)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "notice": {"type": "object"},
                "receiver_aic_version": {
                    "type": "string",
                    "description": (
                        "Optional. Receiver's currently bound AIC "
                        "version. When supplied, V-1 is evaluated and "
                        "should_block reflects the result."
                    ),
                },
                "receiver_has_aic_for_principal": {
                    "type": "boolean",
                    "description": (
                        "Optional. False forces should_block=False per "
                        "V-3 even when V-1 would otherwise apply."
                    ),
                },
            },
            "required": ["notice"],
        },
    },
    "compute_ccc_trend": {
        "description": (
            "Compute the CCCTrend over a list of ConsentCapacityCheck "
            "samples using the reference OLS-slope algorithm. Returns "
            "the canonical enum value (stable/improving/declining/"
            "insufficient_data). Configuration parameters mirror "
            "derive_ccc_trend()."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "samples": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "window_days": {"type": "integer", "minimum": 1},
                "min_samples": {"type": "integer", "minimum": 2},
            },
            "required": ["samples"],
        },
    },
}


def _parse_optional(cls, payload: Any, label: str):
    if payload is None:
        return None
    return _parse(cls, payload, label)


def handle_validate_principal_capability_profile(
    arguments: dict[str, Any],
) -> str:
    payload = arguments.get("pcp")
    if not isinstance(payload, dict):
        raise ToolInvocationError("expected object under key 'pcp'")
    pcp = _parse(PrincipalCapabilityProfile, payload, "pcp")
    return _ok({"principal_id": pcp.principal_id, "version": pcp.version})


def handle_validate_im_precondition(arguments: dict[str, Any]) -> str:
    modality = _parse_optional(
        InteractionModality, arguments.get("modality"), "modality"
    )
    pcp = _parse(PrincipalCapabilityProfile, arguments.get("pcp"), "pcp")
    try:
        validate_im_precondition(modality, pcp)
    except ModalityPreconditionError as exc:
        return _fail(str(exc))
    return _ok({"modality": "precondition-satisfied"})


def handle_validate_language_match(arguments: dict[str, Any]) -> str:
    modality = _parse(
        InteractionModality, arguments.get("modality"), "modality"
    )
    pcp = _parse(PrincipalCapabilityProfile, arguments.get("pcp"), "pcp")
    try:
        validate_language_match(modality, pcp)
    except LanguageMismatchError as exc:
        return _fail(str(exc))
    return _ok({"modality": "language-match"})


def handle_validate_ccc_gate(arguments: dict[str, Any]) -> str:
    pcp = _parse(PrincipalCapabilityProfile, arguments.get("pcp"), "pcp")
    ccc = _parse_optional(
        ConsentCapacityCheck, arguments.get("ccc"), "ccc"
    )
    try:
        validate_ccc_gate(pcp, ccc)
    except CCCGateError as exc:
        return _fail(str(exc))
    return _ok({"gate": "authorized"})


def handle_validate_ccc_privacy(arguments: dict[str, Any]) -> str:
    ccc = _parse(ConsentCapacityCheck, arguments.get("ccc"), "ccc")
    fields = arguments.get("transmitted_fields")
    if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
        raise ToolInvocationError(
            "transmitted_fields must be a list of strings"
        )
    try:
        validate_ccc_privacy(ccc, set(fields))
    except CCCPrivacyError as exc:
        return _fail(str(exc))
    return _ok({"transmitted": sorted(fields)})


def handle_validate_time_window(arguments: dict[str, Any]) -> str:
    contract = _parse(
        AdaptiveInteractionContract, arguments.get("contract"), "contract"
    )
    hhmm = arguments.get("current_time_hhmm")
    if not isinstance(hhmm, str):
        raise ToolInvocationError("current_time_hhmm must be a string")
    is_emergency = arguments.get("is_emergency", False)
    if not isinstance(is_emergency, bool):
        raise ToolInvocationError("is_emergency must be a boolean")
    try:
        validate_time_window(contract, hhmm, is_emergency=is_emergency)
    except TimeWindowViolationError as exc:
        return _fail(str(exc))
    return _ok({"time_window": "inside"})


def handle_validate_option_count(arguments: dict[str, Any]) -> str:
    contract = _parse(
        AdaptiveInteractionContract, arguments.get("contract"), "contract"
    )
    count = arguments.get("options_presented")
    if isinstance(count, bool) or not isinstance(count, int):
        raise ToolInvocationError("options_presented must be an integer")
    try:
        validate_option_count(contract, count)
    except OptionOverloadError as exc:
        return _fail(str(exc))
    return _ok({"options_presented": count})


# ── augmentation_profile extension handlers (AUG-1, AUG-3, AUG-4, AUG-5) ──


def handle_validate_reversibility(arguments: dict[str, Any]) -> str:
    action = _parse(AugmentationAction, arguments.get("action"), "action")
    events_raw = arguments.get("reversion_events")
    if not isinstance(events_raw, list):
        raise ToolInvocationError(
            "reversion_events must be a list of objects"
        )
    events = [
        _parse(AxisRevertedEvent, e, f"reversion_events[{i}]")
        for i, e in enumerate(events_raw)
    ]
    try:
        check_reversibility(action, events)
    except AugmentationError as exc:
        return _fail(str(exc))
    return _ok({"reversibility": "honored"})


def handle_validate_identity_preservation(arguments: dict[str, Any]) -> str:
    profile = _parse(
        AugmentationProfile, arguments.get("profile"), "profile"
    )
    action = _parse(AugmentationAction, arguments.get("action"), "action")
    try:
        check_identity_preservation(profile, action)
    except AugmentationError as exc:
        return _fail(str(exc))
    return _ok({"identity": "preserved"})


def handle_validate_skill_maintenance(arguments: dict[str, Any]) -> str:
    profile = _parse(
        AugmentationProfile, arguments.get("profile"), "profile"
    )
    action = _parse(AugmentationAction, arguments.get("action"), "action")
    try:
        check_skill_maintenance(profile, action)
    except AugmentationError as exc:
        return _fail(str(exc))
    return _ok({"skill_maintenance": "honored"})


def handle_validate_emergency_boundary(arguments: dict[str, Any]) -> str:
    action = _parse(AugmentationAction, arguments.get("action"), "action")
    events_raw = arguments.get("handoff_events")
    if not isinstance(events_raw, list):
        raise ToolInvocationError("handoff_events must be a list of objects")
    events = [
        _parse(HandoffEvent, e, f"handoff_events[{i}]")
        for i, e in enumerate(events_raw)
    ]
    try:
        check_emergency_boundary(action, events)
    except AugmentationError as exc:
        return _fail(str(exc))
    return _ok({"emergency_boundary": "honored"})


def handle_validate_accessibility_service_ref(arguments: dict[str, Any]) -> str:
    payload = arguments.get("ref")
    if not isinstance(payload, dict):
        raise ToolInvocationError("expected object under key 'ref'")
    _parse(AccessibilityServiceRef, payload, "ref")
    return _ok({"ref": "valid"})


def handle_validate_active_challenge(arguments: dict[str, Any]) -> str:
    payload = arguments.get("challenge")
    if not isinstance(payload, dict):
        raise ToolInvocationError("expected object under key 'challenge'")
    _parse(ActiveChallenge, payload, "challenge")
    return _ok({"challenge": "valid"})


def handle_validate_pace_consent_annotation(arguments: dict[str, Any]) -> str:
    payload = arguments.get("annotation")
    if not isinstance(payload, dict):
        raise ToolInvocationError("expected object under key 'annotation'")
    annotation = _parse(PACEConsentAnnotation, payload, "annotation")
    # Referential coherence checks beyond what pydantic enforces:
    # CCC fields MUST be populated when ccc_performed is True.
    if annotation.ccc_performed:
        missing = [
            name for name in (
                "ccc_capacity_signal",
                "ccc_recommendation",
                "ccc_assessment_method",
            )
            if getattr(annotation, name) is None
        ]
        if missing:
            return _fail(
                "ccc_performed=true but the following fields are absent: "
                + ", ".join(missing)
            )
        from pace.types import AssessmentMethod
        if (
            annotation.ccc_assessment_method == AssessmentMethod.ACTIVE
            and annotation.active_challenge is None
        ):
            return _fail(
                "ccc_assessment_method=ACTIVE requires an active_challenge "
                "record"
            )
    return _ok({"annotation": "valid"})


def handle_validate_pace_violation_notice(arguments: dict[str, Any]) -> str:
    """Validate a PACEViolationNotice and report V-1/V-2/V-3 enforcement.

    The handler does NOT mutate any block list; it returns the structured
    decision a receiving orchestrator should apply.
    """
    payload = arguments.get("notice")
    if not isinstance(payload, dict):
        raise ToolInvocationError("expected object under key 'notice'")
    notice = _parse(PACEViolationNotice, payload, "notice")

    receiver_aic_version = arguments.get("receiver_aic_version")
    receiver_has_aic = arguments.get("receiver_has_aic_for_principal")
    if receiver_has_aic is not None and not isinstance(receiver_has_aic, bool):
        raise ToolInvocationError(
            "receiver_has_aic_for_principal must be a boolean"
        )

    # Default to "no opinion supplied" -> should_block reflects only
    # whether V-1 *could* apply on AIC version match.
    should_block: bool
    if receiver_has_aic is False:
        # V-3: no AIC for this principal -> log only, do not block.
        should_block = False
    elif receiver_aic_version is not None:
        if not isinstance(receiver_aic_version, str):
            raise ToolInvocationError(
                "receiver_aic_version must be a string"
            )
        should_block = receiver_aic_version == notice.aic_version
    else:
        should_block = False  # caller did not supply enough context

    return _ok(
        {
            "notice_id": notice.notice_id,
            "should_block": should_block,
            "block_duration_seconds": notice.block_duration_seconds,
            "block_until_timestamp": notice.detected_at,
            "forwarding_allowed": False,  # V-2: one-hop only
            "evaluated_rule": "V-3" if receiver_has_aic is False else "V-1",
        }
    )


def handle_compute_ccc_trend(arguments: dict[str, Any]) -> str:
    samples_raw = arguments.get("samples")
    if not isinstance(samples_raw, list):
        raise ToolInvocationError("samples must be a list of objects")
    samples = [
        _parse(ConsentCapacityCheck, s, f"samples[{i}]")
        for i, s in enumerate(samples_raw)
    ]
    kwargs: dict[str, Any] = {}
    for k in ("window_days", "min_samples"):
        v = arguments.get(k)
        if v is not None:
            if isinstance(v, bool) or not isinstance(v, int):
                raise ToolInvocationError(f"{k} must be an integer")
            kwargs[k] = v
    trend: CCCTrend = derive_ccc_trend(samples, **kwargs)
    return _ok({"trend": trend.value, "samples_in_window": len(samples)})


HANDLERS: dict[str, Any] = {
    "validate_principal_capability_profile": handle_validate_principal_capability_profile,
    "validate_im_precondition": handle_validate_im_precondition,
    "validate_language_match": handle_validate_language_match,
    "validate_ccc_gate": handle_validate_ccc_gate,
    "validate_ccc_privacy": handle_validate_ccc_privacy,
    "validate_time_window": handle_validate_time_window,
    "validate_option_count": handle_validate_option_count,
    # augmentation_profile extension
    "validate_reversibility": handle_validate_reversibility,
    "validate_identity_preservation": handle_validate_identity_preservation,
    "validate_skill_maintenance": handle_validate_skill_maintenance,
    "validate_emergency_boundary": handle_validate_emergency_boundary,
    # AgentCard descriptor + sibling primitives
    "validate_accessibility_service_ref": handle_validate_accessibility_service_ref,
    "validate_active_challenge": handle_validate_active_challenge,
    "validate_pace_consent_annotation": handle_validate_pace_consent_annotation,
    "validate_pace_violation_notice": handle_validate_pace_violation_notice,
    "compute_ccc_trend": handle_compute_ccc_trend,
}


def list_tool_names() -> list[str]:
    return list(TOOL_SCHEMAS.keys())
