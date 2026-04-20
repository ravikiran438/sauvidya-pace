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

Each tool wraps one of the six named accessibility validators from the
PACE specification. Failures return ``{"ok": false, "error": ...}``
with the validator's own diagnostic message.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from pace.types import (
    AdaptiveInteractionContract,
    ConsentCapacityCheck,
    InteractionModality,
    PrincipalCapabilityProfile,
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
}


def _parse_optional(cls, payload: Any, label: str):
    if payload is None:
        return None
    return _parse(cls, payload, label)


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


HANDLERS: dict[str, Any] = {
    "validate_im_precondition": handle_validate_im_precondition,
    "validate_language_match": handle_validate_language_match,
    "validate_ccc_gate": handle_validate_ccc_gate,
    "validate_ccc_privacy": handle_validate_ccc_privacy,
    "validate_time_window": handle_validate_time_window,
    "validate_option_count": handle_validate_option_count,
}


def list_tool_names() -> list[str]:
    return list(TOOL_SCHEMAS.keys())
