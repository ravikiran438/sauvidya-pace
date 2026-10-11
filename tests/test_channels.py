# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""IM-1 channels: every channel in a plan reaches her; no silent dead end."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pace.types import (
    AccessibilityServiceRef,
    FallbackEntry,
    InteractionModality,
    ModalityPlan,
    PrincipalCapabilityProfile,
)
from pace.validators import ChannelError, validate_channels


def _pcp(**caps) -> PrincipalCapabilityProfile:
    return PrincipalCapabilityProfile(
        principal_id="Lakshmi", version="v1",
        declared_at="2026-10-01T10:00:00+05:30", declared_by="guardian:ravi",
        language=[{"code": "te", "fluency": 1.0}], **caps,
    )


def _modality(primary="voice", fallbacks=(), escalation_target=None) -> InteractionModality:
    return InteractionModality(
        agent_id="a1", principal_id="Lakshmi", pcp_version="v1",
        modality_plan=ModalityPlan(primary_channel=primary, language="te"),
        fallback_chain=[FallbackEntry(channel=c, condition=f"{c} unavailable") for c in fallbacks],
        escalation_target=escalation_target,
    )


def _ref(*modalities) -> AccessibilityServiceRef:
    return AccessibilityServiceRef(
        version="0.1.0",
        pcp_endpoint="https://orch.example.com/pace/pcp",
        aic_endpoint="https://orch.example.com/pace/aic/{principal_id}",
        violation_notice_endpoint="https://orch.example.com/pace/violations",
        supported_modalities=list(modalities),
        supported_languages=["te"],
    )


def test_paper_example_voice_then_guardian_relay():
    validate_channels(_modality("voice", ["guardian_relay"]), _pcp(vision="low"))


def test_text_fallback_rejected_when_she_cannot_read():
    """Voice is down; the plan falls back to a text message she cannot read."""
    with pytest.raises(ChannelError, match="fallback 1 channel 'text': she cannot read"):
        validate_channels(_modality("voice", ["text", "guardian_relay"]), _pcp(literacy="none"))


def test_voice_rejected_when_she_cannot_hear():
    with pytest.raises(ChannelError, match="primary channel 'voice': she cannot hear"):
        validate_channels(_modality("voice", ["guardian_relay"]), _pcp(hearing="none"))


def test_visual_rejected_when_she_cannot_see():
    with pytest.raises(ChannelError, match="she cannot see"):
        validate_channels(_modality("visual", ["guardian_relay"]), _pcp(vision="none"))


def test_haptic_always_reaches():
    validate_channels(_modality("haptic", ["guardian_relay"]), _pcp(vision="none", hearing="none"))


def test_chain_that_can_dead_end_rejected():
    with pytest.raises(ChannelError, match="left unreached"):
        validate_channels(_modality("voice", ["text"]), _pcp())


def test_escalation_target_closes_the_chain():
    validate_channels(_modality("voice", [], escalation_target="guardian:ravi"), _pcp())


def test_channel_the_agent_cannot_drive_rejected():
    with pytest.raises(ChannelError, match="not among the agent's supported modalities"):
        validate_channels(_modality("voice", ["text", "guardian_relay"]), _pcp(), _ref("voice"))
    validate_channels(_modality("voice", ["text", "guardian_relay"]), _pcp(), _ref("voice", "text"))


def test_one_channel_vocabulary():
    """The paper's 'text_large_font' and the old card example 'large_text'
    are not channels; there is one vocabulary."""
    with pytest.raises(ValidationError):
        FallbackEntry(channel="text_large_font", condition="voice unavailable")
    with pytest.raises(ValidationError):
        _ref("voice", "large_text")


def test_guardian_relay_is_fallback_only():
    with pytest.raises(ValidationError):
        ModalityPlan(primary_channel="guardian_relay", language="te")
