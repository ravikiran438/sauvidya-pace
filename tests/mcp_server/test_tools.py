# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the PACE MCP server tool handlers.

Covers each of the six named invariants through the JSON contract
exposed to an MCP client.
"""

from __future__ import annotations

import json

import pytest

from pace.mcp_server.tools import (
    HANDLERS,
    TOOL_SCHEMAS,
    ToolInvocationError,
    handle_validate_ccc_gate,
    handle_validate_ccc_privacy,
    handle_validate_emergency_boundary,
    handle_validate_identity_preservation,
    handle_validate_im_precondition,
    handle_validate_language_match,
    handle_validate_option_count,
    handle_validate_principal_capability_profile,
    handle_validate_reversibility,
    handle_validate_skill_maintenance,
    handle_validate_time_window,
    list_tool_names,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


def _pcp(decision_capacity: str = "fluctuating", lang: str = "te") -> dict:
    return {
        "principal_id": "p1",
        "version": "v1",
        "declared_at": "2026-04-17T10:00:00Z",
        "declared_by": "guardian:g1",
        "language": [{"code": lang, "fluency": 1.0}],
        "decision_capacity": decision_capacity,
    }


def _modality(lang: str = "te", pcp_version: str = "v1") -> dict:
    return {
        "agent_id": "a1",
        "principal_id": "p1",
        "pcp_version": pcp_version,
        "modality_plan": {
            "primary_channel": "voice",
            "language": lang,
            "max_options": 2,
            "timeout_seconds": 300,
        },
    }


def _ccc(recommendation: str = "proceed") -> dict:
    return {
        "principal_id": "p1",
        "timestamp": "2026-04-17T10:15:00Z",
        "capacity_signal": 0.82,
        "confidence": 0.75,
        "assessment_method": "passive",
        "pcp_version": "v1",
        "recommendation": recommendation,
    }


def _contract(lang: str = "te") -> dict:
    return {
        "principal_id": "p1",
        "pcp_version": "v1",
        "interaction_rules": {
            "language": lang,
            "valid_time_windows": [
                {"start": "09:00", "end": "11:00"},
                {"start": "14:00", "end": "16:00"},
            ],
            "sundown_block": {"start": "17:00", "end": "08:00"},
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────


def test_schemas_and_handlers_consistent():
    assert set(TOOL_SCHEMAS.keys()) == set(HANDLERS.keys())
    assert set(list_tool_names()) == set(HANDLERS.keys())


def test_all_schemas_have_shape():
    for name, schema in TOOL_SCHEMAS.items():
        assert "description" in schema, f"{name} missing description"
        assert "inputSchema" in schema, f"{name} missing inputSchema"
        assert schema["inputSchema"]["type"] == "object"


# ─────────────────────────────────────────────────────────────────────────────
# validate_principal_capability_profile (standalone PCP structural check)
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_pcp_happy_path():
    result = json.loads(
        handle_validate_principal_capability_profile({"pcp": _pcp()})
    )
    assert result["ok"] is True
    assert result["principal_id"] == "p1"
    assert result["version"] == "v1"


def test_validate_pcp_rejects_missing_language():
    pcp = _pcp()
    del pcp["language"]
    with pytest.raises(ToolInvocationError, match="invalid pcp"):
        handle_validate_principal_capability_profile({"pcp": pcp})


def test_validate_pcp_rejects_non_object():
    with pytest.raises(ToolInvocationError, match="expected object"):
        handle_validate_principal_capability_profile({"pcp": "not-a-dict"})


# ─────────────────────────────────────────────────────────────────────────────
# IM-1 precondition
# ─────────────────────────────────────────────────────────────────────────────


def test_im_precondition_valid():
    result = json.loads(
        handle_validate_im_precondition(
            {"modality": _modality(), "pcp": _pcp()}
        )
    )
    assert result["ok"] is True


def test_im_precondition_no_modality_fails():
    result = json.loads(
        handle_validate_im_precondition({"modality": None, "pcp": _pcp()})
    )
    assert result["ok"] is False
    assert "IM-1" in result["error"]


def test_im_precondition_version_mismatch_fails():
    result = json.loads(
        handle_validate_im_precondition(
            {"modality": _modality(pcp_version="v0"), "pcp": _pcp()}
        )
    )
    assert result["ok"] is False
    assert "IM-1" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# IM-2 language match
# ─────────────────────────────────────────────────────────────────────────────


def test_language_match_ok():
    result = json.loads(
        handle_validate_language_match(
            {"modality": _modality(lang="te"), "pcp": _pcp(lang="te")}
        )
    )
    assert result["ok"] is True


def test_language_mismatch_fails():
    result = json.loads(
        handle_validate_language_match(
            {"modality": _modality(lang="en"), "pcp": _pcp(lang="te")}
        )
    )
    assert result["ok"] is False
    assert "IM-2" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# CCC-1 gate
# ─────────────────────────────────────────────────────────────────────────────


def test_ccc_gate_fluctuating_proceed_ok():
    result = json.loads(
        handle_validate_ccc_gate(
            {"pcp": _pcp("fluctuating"), "ccc": _ccc("proceed")}
        )
    )
    assert result["ok"] is True


def test_ccc_gate_fluctuating_no_check_fails():
    result = json.loads(
        handle_validate_ccc_gate({"pcp": _pcp("fluctuating"), "ccc": None})
    )
    assert result["ok"] is False
    assert "CCC-1" in result["error"]


def test_ccc_gate_stable_no_check_ok():
    result = json.loads(
        handle_validate_ccc_gate({"pcp": _pcp("stable"), "ccc": None})
    )
    assert result["ok"] is True


def test_ccc_gate_fluctuating_defer_fails():
    result = json.loads(
        handle_validate_ccc_gate(
            {"pcp": _pcp("fluctuating"), "ccc": _ccc("defer")}
        )
    )
    assert result["ok"] is False


# ─────────────────────────────────────────────────────────────────────────────
# CCC-2 privacy
# ─────────────────────────────────────────────────────────────────────────────


def test_ccc_privacy_no_leak():
    result = json.loads(
        handle_validate_ccc_privacy(
            {
                "ccc": _ccc(),
                "transmitted_fields": ["interaction_status", "agent_id"],
            }
        )
    )
    assert result["ok"] is True


def test_ccc_privacy_capacity_signal_leak_fails():
    result = json.loads(
        handle_validate_ccc_privacy(
            {
                "ccc": _ccc(),
                "transmitted_fields": ["capacity_signal", "agent_id"],
            }
        )
    )
    assert result["ok"] is False
    assert "CCC-2" in result["error"]


def test_ccc_privacy_non_string_list_raises():
    with pytest.raises(ToolInvocationError, match="list of strings"):
        handle_validate_ccc_privacy(
            {"ccc": _ccc(), "transmitted_fields": [1, 2, 3]}
        )


# ─────────────────────────────────────────────────────────────────────────────
# AIC-1 time window
# ─────────────────────────────────────────────────────────────────────────────


def test_time_window_morning_ok():
    result = json.loads(
        handle_validate_time_window(
            {"contract": _contract(), "current_time_hhmm": "10:00"}
        )
    )
    assert result["ok"] is True


def test_time_window_sundown_fails():
    result = json.loads(
        handle_validate_time_window(
            {"contract": _contract(), "current_time_hhmm": "19:00"}
        )
    )
    assert result["ok"] is False
    assert "AIC-1" in result["error"]


def test_time_window_emergency_overrides():
    result = json.loads(
        handle_validate_time_window(
            {
                "contract": _contract(),
                "current_time_hhmm": "19:00",
                "is_emergency": True,
            }
        )
    )
    assert result["ok"] is True


def test_time_window_non_string_time_raises():
    with pytest.raises(ToolInvocationError, match="must be a string"):
        handle_validate_time_window(
            {"contract": _contract(), "current_time_hhmm": 1000}
        )


# ─────────────────────────────────────────────────────────────────────────────
# AIC-2 option count
# ─────────────────────────────────────────────────────────────────────────────


def test_option_count_within_limit_ok():
    result = json.loads(
        handle_validate_option_count(
            {"contract": _contract(), "options_presented": 2}
        )
    )
    assert result["ok"] is True


def test_option_count_over_limit_fails():
    result = json.loads(
        handle_validate_option_count(
            {"contract": _contract(), "options_presented": 5}
        )
    )
    assert result["ok"] is False
    assert "AIC-2" in result["error"]


def test_option_count_non_integer_raises():
    with pytest.raises(ToolInvocationError, match="must be an integer"):
        handle_validate_option_count(
            {"contract": _contract(), "options_presented": "five"}
        )


# ─────────────────────────────────────────────────────────────────────────────
# augmentation_profile extension handlers
# ─────────────────────────────────────────────────────────────────────────────


def _aug_profile_payload(identity_consent: bool = False) -> dict:
    return {
        "principal_id": "user-123",
        "pcp_version": "2026-04-25.v1",
        "axes": [
            {"name": "social_interpretation", "kind": "compensate"},
            {"name": "executive_function", "kind": "compensate"},
            {"name": "independent_email", "kind": "preserve"},
        ],
        "emergency_triggers": [
            {"name": "medical_keyword", "description": "med phrase detected"}
        ],
        "identity_consent": identity_consent,
        "declared_at": "2026-04-25T12:00:00+00:00",
        "declared_by": "principal",
    }


def _aug_action_payload(
    axis_name: str = "social_interpretation",
    mediation: str = "agent_compensated",
    alters_identity: bool = False,
    at: str = "2026-04-25T13:00:00+00:00",
) -> dict:
    return {
        "principal_id": "user-123",
        "axis_name": axis_name,
        "mediation": mediation,
        "alters_identity": alters_identity,
        "description": "test action",
        "at": at,
    }


def test_validate_reversibility_passes_with_no_reversion():
    result = json.loads(
        handle_validate_reversibility(
            {"action": _aug_action_payload(), "reversion_events": []}
        )
    )
    assert result["ok"] is True


def test_validate_reversibility_rejects_action_after_reversion():
    reversion = {
        "principal_id": "user-123",
        "axis_name": "social_interpretation",
        "reverted_at": "2026-04-25T12:30:00+00:00",
        "reverted_by": "principal",
    }
    result = json.loads(
        handle_validate_reversibility(
            {
                "action": _aug_action_payload(at="2026-04-25T13:00:00+00:00"),
                "reversion_events": [reversion],
            }
        )
    )
    assert result["ok"] is False
    assert "was reverted" in result["error"]


def test_validate_identity_preservation_passes_without_alteration():
    result = json.loads(
        handle_validate_identity_preservation(
            {"profile": _aug_profile_payload(), "action": _aug_action_payload()}
        )
    )
    assert result["ok"] is True


def test_validate_identity_preservation_rejects_alteration_without_consent():
    result = json.loads(
        handle_validate_identity_preservation(
            {
                "profile": _aug_profile_payload(identity_consent=False),
                "action": _aug_action_payload(alters_identity=True),
            }
        )
    )
    assert result["ok"] is False
    assert "identity_consent" in result["error"]


def test_validate_skill_maintenance_passes_for_compensate_axis():
    result = json.loads(
        handle_validate_skill_maintenance(
            {
                "profile": _aug_profile_payload(),
                "action": _aug_action_payload(axis_name="social_interpretation"),
            }
        )
    )
    assert result["ok"] is True


def test_validate_skill_maintenance_rejects_preserve_axis():
    result = json.loads(
        handle_validate_skill_maintenance(
            {
                "profile": _aug_profile_payload(),
                "action": _aug_action_payload(axis_name="independent_email"),
            }
        )
    )
    assert result["ok"] is False
    assert "preserve" in result["error"]


def test_validate_emergency_boundary_passes_with_no_handoff():
    result = json.loads(
        handle_validate_emergency_boundary(
            {"action": _aug_action_payload(), "handoff_events": []}
        )
    )
    assert result["ok"] is True


def test_validate_emergency_boundary_rejects_action_during_unacked_handoff():
    handoff = {
        "principal_id": "user-123",
        "trigger_name": "medical_keyword",
        "fired_at": "2026-04-25T12:30:00+00:00",
    }
    result = json.loads(
        handle_validate_emergency_boundary(
            {
                "action": _aug_action_payload(at="2026-04-25T13:00:00+00:00"),
                "handoff_events": [handoff],
            }
        )
    )
    assert result["ok"] is False
    assert "awaiting human" in result["error"]


def test_validate_emergency_boundary_passes_after_acknowledgement():
    handoff = {
        "principal_id": "user-123",
        "trigger_name": "medical_keyword",
        "fired_at": "2026-04-25T12:00:00+00:00",
        "human_acknowledged_at": "2026-04-25T12:10:00+00:00",
        "human_acknowledged_by": "ops-staff",
    }
    result = json.loads(
        handle_validate_emergency_boundary(
            {
                "action": _aug_action_payload(at="2026-04-25T13:00:00+00:00"),
                "handoff_events": [handoff],
            }
        )
    )
    assert result["ok"] is True
