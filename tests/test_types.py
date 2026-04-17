# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for PACE type construction and bounds."""

import pytest
from pace.types import *


class TestPrincipalCapabilityProfile:
    def test_basic_construction(self):
        pcp = PrincipalCapabilityProfile(
            principal_id="p1", version="v1",
            declared_at="2026-04-17T10:00:00Z", declared_by="principal",
            language=[LanguageFluency(code="te", fluency=1.0)],
        )
        assert pcp.vision == CapabilityLevel.FULL
        assert pcp.decision_capacity == DecisionCapacity.STABLE

    def test_requires_at_least_one_language(self):
        with pytest.raises(Exception):
            PrincipalCapabilityProfile(
                principal_id="p1", version="v1",
                declared_at="2026-04-17T10:00:00Z", declared_by="principal",
                language=[],
            )

    def test_guardian_declaration(self):
        pcp = PrincipalCapabilityProfile(
            principal_id="p1", version="v1",
            declared_at="2026-04-17T10:00:00Z",
            declared_by="guardian:g-ravi-us",
            language=[LanguageFluency(code="te", fluency=1.0)],
            cognitive=CognitiveLevel.MODERATE_DECLINE,
            decision_capacity=DecisionCapacity.FLUCTUATING,
        )
        assert pcp.declared_by.startswith("guardian:")

    def test_correction_of(self):
        pcp = PrincipalCapabilityProfile(
            principal_id="p1", version="v2",
            declared_at="2026-04-17T10:00:00Z",
            declared_by="guardian:g-ravi-us",
            language=[LanguageFluency(code="te", fluency=1.0)],
            correction_of="v1",
        )
        assert pcp.correction_of == "v1"


class TestInteractionModality:
    def test_basic_construction(self):
        im = InteractionModality(
            agent_id="a1", principal_id="p1", pcp_version="v1",
            modality_plan=ModalityPlan(
                primary_channel=PrimaryChannel.VOICE,
                language="te", speech_rate=0.7,
                max_options=2, timeout_seconds=300,
            ),
        )
        assert im.modality_plan.primary_channel == PrimaryChannel.VOICE

    def test_speech_rate_bounds(self):
        with pytest.raises(Exception):
            ModalityPlan(
                primary_channel=PrimaryChannel.VOICE,
                language="te", speech_rate=1.5,
            )


class TestConsentCapacityCheck:
    def test_basic_construction(self):
        ccc = ConsentCapacityCheck(
            principal_id="p1", timestamp="2026-04-17T10:15:00Z",
            capacity_signal=0.82, confidence=0.75,
            assessment_method=AssessmentMethod.PASSIVE,
            pcp_version="v1",
            recommendation=CapacityRecommendation.PROCEED,
        )
        assert ccc.recommendation == CapacityRecommendation.PROCEED

    def test_capacity_signal_bounds(self):
        with pytest.raises(Exception):
            ConsentCapacityCheck(
                principal_id="p1", timestamp="2026-04-17T10:15:00Z",
                capacity_signal=1.5, confidence=0.5,
                assessment_method=AssessmentMethod.PASSIVE,
                pcp_version="v1",
                recommendation=CapacityRecommendation.PROCEED,
            )

    def test_all_recommendations(self):
        for rec in CapacityRecommendation:
            ccc = ConsentCapacityCheck(
                principal_id="p1", timestamp="2026-04-17T10:15:00Z",
                capacity_signal=0.5, confidence=0.5,
                assessment_method=AssessmentMethod.PASSIVE,
                pcp_version="v1", recommendation=rec,
            )
            assert ccc.recommendation == rec


class TestAdaptiveInteractionContract:
    def test_basic_construction(self):
        aic = AdaptiveInteractionContract(
            principal_id="p1", pcp_version="v1",
            interaction_rules=InteractionRules(
                language="te",
                valid_time_windows=[
                    TimeWindow(start="09:00", end="11:00"),
                    TimeWindow(start="14:00", end="16:00"),
                ],
                sundown_block=TimeWindow(start="17:00", end="08:00"),
            ),
        )
        assert aic.interaction_rules.max_options_per_turn == 2
        assert len(aic.interaction_rules.valid_time_windows) == 2
