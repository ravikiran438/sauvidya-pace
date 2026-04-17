# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""InteractionModality: agent's adapted communication plan (paper Section 3.2).

Invariant IM-1: MUST be computed from PCP before any interaction.
Invariant IM-2: Language mismatch MUST NOT default to English.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PrimaryChannel(str, Enum):
    VOICE = "voice"
    TEXT = "text"
    VISUAL = "visual"
    HAPTIC = "haptic"


class FallbackEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    channel: str
    condition: str


class ModalityPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    primary_channel: PrimaryChannel
    language: str = Field(..., description="ISO 639-1 code")
    speech_rate: float = Field(default=1.0, gt=0.0, le=1.0)
    information_density: str = Field(default="medium", description="low | medium | high")
    max_options: int = Field(default=5, gt=0)
    confirmation_style: str = Field(default="none")
    memory_aid: bool = Field(default=False)
    timeout_seconds: int = Field(default=60, gt=0)


class InteractionModality(BaseModel):
    """How an agent will communicate with a specific principal,
    computed from their PrincipalCapabilityProfile."""

    model_config = ConfigDict(str_strip_whitespace=True)

    agent_id: str
    principal_id: str
    pcp_version: str
    modality_plan: ModalityPlan
    fallback_chain: List[FallbackEntry] = Field(default_factory=list)
    escalation_target: Optional[str] = Field(
        default=None,
        description="Guardian or alternative agent for escalation",
    )
