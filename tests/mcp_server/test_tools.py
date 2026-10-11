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
    handle_validate_contract_language,
    handle_validate_relay_consent,
    handle_validate_option_count,
    handle_validate_modality_contract,
    handle_enforce_violation,
    handle_validate_retry,
    handle_validate_daily_limit,
    handle_validate_principal_capability_profile,
    handle_validate_reversibility,
    handle_validate_skill_maintenance,
    handle_validate_step_up,
    handle_check_step_up_nudge,
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
            "timezone": "Asia/Kolkata",
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
            {"contract": _contract(), "at": "2026-10-10T10:00:00+05:30"}
        )
    )
    assert result["ok"] is True


def test_time_window_sundown_fails():
    result = json.loads(
        handle_validate_time_window(
            {"contract": _contract(), "at": "2026-10-10T08:30:00-05:00"}
        )
    )
    assert result["ok"] is False
    assert "AIC-1" in result["error"]


def test_time_window_emergency_overrides():
    result = json.loads(
        handle_validate_time_window(
            {
                "contract": _contract(),
                "at": "2026-10-10T19:00:00+05:30",
                "is_emergency": True,
            }
        )
    )
    assert result["ok"] is True


def test_time_window_non_string_time_raises():
    with pytest.raises(ToolInvocationError, match="ISO 8601"):
        handle_validate_time_window({"contract": _contract(), "at": 1000})


def test_time_window_requires_utc_offset():
    with pytest.raises(ToolInvocationError, match="zone-aware"):
        handle_validate_time_window(
            {"contract": _contract(), "at": "2026-10-10T10:00:00"}
        )


def test_time_window_reports_principal_local_time():
    result = json.loads(
        handle_validate_time_window(
            {"contract": _contract(), "at": "2026-10-09T23:30:00-05:00"}
        )
    )
    assert result["ok"] is True
    assert result["principal_local_time"] == "2026-10-10T10:00+05:30"


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
        "version": "v1",
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
        "profile_version": "v1",
        "task_id": "task-1",
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


def _step_up_payload(**overrides) -> dict:
    payload = {
        "principal_id": "user-123",
        "axis_name": "social_interpretation",
        "task_id": "task-1",
        "granted_at": "2026-04-25T12:50:00+00:00",
        "expires_at": "2026-04-25T13:20:00+00:00",
    }
    payload.update(overrides)
    return payload


def test_validate_step_up_rejects_agent_action_in_stepped_up_task():
    result = json.loads(
        handle_validate_step_up(
            {"action": _aug_action_payload(), "step_up_events": [_step_up_payload()]}
        )
    )
    assert result["ok"] is False
    assert "AUG-6" in result["error"]


def test_validate_step_up_passes_in_other_task():
    result = json.loads(
        handle_validate_step_up(
            {
                "action": _aug_action_payload(),
                "step_up_events": [_step_up_payload(task_id="task-2")],
            }
        )
    )
    assert result["ok"] is True


def test_check_step_up_nudge_reports_due_after_time_limit():
    due = json.loads(
        handle_check_step_up_nudge(
            {"step_up": _step_up_payload(), "now": "2026-04-25T13:30:00+00:00"}
        )
    )
    assert due["ok"] is True and due["nudge_due"] is True
    not_due = json.loads(
        handle_check_step_up_nudge(
            {"step_up": _step_up_payload(), "now": "2026-04-25T13:00:00+00:00"}
        )
    )
    assert not_due["nudge_due"] is False


def test_check_step_up_nudge_rejects_bad_timestamp():
    with pytest.raises(ToolInvocationError, match="ISO 8601"):
        handle_check_step_up_nudge({"step_up": _step_up_payload(), "now": "soon"})


def _lakshmi_pcp() -> dict:
    return {
        "principal_id": "p1",
        "version": "v1",
        "declared_at": "2026-10-01T10:00:00+05:30",
        "declared_by": "guardian:g1",
        "language": [{"code": "te", "fluency": 1.0}, {"code": "en", "fluency": 0.3}],
        "decision_capacity": "fluctuating",
        "adaptations_required": ["language:te"],
    }


def test_language_match_rejects_english_for_pinned_telugu():
    modality = {
        "agent_id": "a1", "principal_id": "p1", "pcp_version": "v1",
        "modality_plan": {"primary_channel": "voice", "language": "en"},
    }
    result = json.loads(
        handle_validate_language_match({"modality": modality, "pcp": _lakshmi_pcp()})
    )
    assert result["ok"] is False
    assert "language:te" in result["error"]


def test_contract_language_rejects_english_contract():
    contract = {
        "principal_id": "p1", "pcp_version": "v1",
        "interaction_rules": {"language": "en", "timezone": "Asia/Kolkata"},
    }
    result = json.loads(
        handle_validate_contract_language({"contract": contract, "pcp": _lakshmi_pcp()})
    )
    assert result["ok"] is False and "AIC" in result["error"]


def test_relay_consent_requires_principal_ccc():
    annotation = {
        "annotation_id": "ann-1", "consent_record_id": "cr-1",
        "principal_id": "p1", "pcp_version": "v1",
        "relayed_by": "guardian:g1", "ccc_performed": False,
        "interaction_modality": {"primary_channel": "voice", "language": "te"},
        "annotated_at": "2026-10-09T10:00:00Z",
    }
    result = json.loads(
        handle_validate_relay_consent({"pcp": _lakshmi_pcp(), "annotation": annotation})
    )
    assert result["ok"] is False and "CCC-4" in result["error"]


def test_modality_contract_rejects_short_timeout():
    modality = {
        "agent_id": "a1", "principal_id": "p1", "pcp_version": "v1",
        "modality_plan": {
            "primary_channel": "voice", "language": "te", "speech_rate": 0.7,
            "information_density": "low", "max_options": 2,
            "confirmation_style": "voice_repeat_back", "memory_aid": True,
            "timeout_seconds": 60,
        },
    }
    result = json.loads(
        handle_validate_modality_contract({"modality": modality, "contract": _contract()})
    )
    assert result["ok"] is False and "AIC-5" in result["error"]
    modality["modality_plan"]["timeout_seconds"] = 300
    result = json.loads(
        handle_validate_modality_contract({"modality": modality, "contract": _contract()})
    )
    assert result["ok"] is True


def test_enforce_violation_returns_guardian_notification():
    result = json.loads(
        handle_enforce_violation(
            {
                "contract": _contract(),
                "violation_type": "time_window",
                "agent_id": "booking-agent",
                "at": "2026-10-10T08:10:00-05:00",
                "guardian_timezone": "America/Chicago",
            }
        )
    )
    assert result["ok"] is True
    assert result["broadcast_block"] is True
    assert result["notification"]["principal_local_time"] == "18:40 IST (Sat 10 Oct)"


def test_enforce_violation_rejects_unknown_type():
    with pytest.raises(ToolInvocationError, match="cannot enforce"):
        handle_enforce_violation(
            {"contract": _contract(), "violation_type": "rudeness",
             "agent_id": "a1", "at": "2026-10-10T08:10:00-05:00"}
        )


def test_validate_retry_same_window_rejected():
    payload = {
        "contract": _contract(),
        "prior_attempts": [{"at": "2026-10-10T10:15:00+05:30", "responded": False}],
        "at": "2026-10-10T10:20:00+05:30",
    }
    assert json.loads(handle_validate_retry(payload))["ok"] is False
    payload["at"] = "2026-10-10T14:00:00+05:30"
    assert json.loads(handle_validate_retry(payload))["ok"] is True


def test_validate_retry_bad_attempt_raises():
    with pytest.raises(ToolInvocationError, match="bad attempt"):
        handle_validate_retry(
            {"contract": _contract(), "prior_attempts": [{"at": "soon"}], "at": "2026-10-10T14:00:00+05:30"}
        )


def test_validate_daily_limit_reports_remaining_then_blocks():
    calls = [{"at": f"2026-10-10T{h}:00:00+05:30", "responded": True} for h in ("09", "10")]
    ok = json.loads(handle_validate_daily_limit(
        {"contract": _contract(), "prior_contacts": calls, "at": "2026-10-10T14:00:00+05:30"}))
    assert ok["ok"] is True and ok["remaining_today"] == 1
    calls.append({"at": "2026-10-10T14:00:00+05:30", "responded": False})
    blocked = json.loads(handle_validate_daily_limit(
        {"contract": _contract(), "prior_contacts": calls, "at": "2026-10-10T15:00:00+05:30"}))
    assert blocked["ok"] is False and "AIC-1" in blocked["error"]
