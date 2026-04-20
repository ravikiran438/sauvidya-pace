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
    handle_validate_im_precondition,
    handle_validate_language_match,
    handle_validate_option_count,
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
