# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Lock-in tests for PACE's published extension URIs and ResponseClassification."""

from __future__ import annotations

from pace.types import PACE_EXTENSION_URI, ResponseClassification


def test_pace_core_extension_uri():
    assert PACE_EXTENSION_URI == (
        "https://ravikiran438.github.io/sauvidya-pace/v1"
    )


def test_augmentation_profile_extension_uri():
    from pace.extensions.augmentation_profile import EXTENSION_URI
    assert EXTENSION_URI == (
        "https://github.com/ravikiran438/sauvidya-pace/"
        "extensions/augmentation-profile/v1"
    )


def test_response_classification_canonical_values():
    """Wire format depends on these exact strings."""
    assert {m.value for m in ResponseClassification} == {
        "comprehended",
        "partial",
        "non_responsive",
        "refused",
    }


def test_response_classification_string_round_trip():
    assert ResponseClassification("comprehended") is ResponseClassification.COMPREHENDED
    assert ResponseClassification("non_responsive") is ResponseClassification.NON_RESPONSIVE
