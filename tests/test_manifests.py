# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Drift guard: committed manifests and SPEC.md files match the generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from pace import __version__
from pace.manifest import augmentation_manifest, core_manifest, invariant_id, outputs

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("path", sorted(outputs(ROOT)), ids=lambda p: str(p.relative_to(ROOT)))
def test_committed_file_matches_generator(path: Path):
    expected = outputs(ROOT)[path]
    assert path.exists(), f"{path} missing; run `uv run python -m pace.manifest --write`"
    assert path.read_text(encoding="utf-8") == expected, (
        f"{path.relative_to(ROOT)} is stale; run `uv run python -m pace.manifest --write`"
    )


@pytest.mark.parametrize("build", [core_manifest, augmentation_manifest])
def test_manifest_version_tracks_package(build):
    assert build()["extension"]["version"] == __version__


def test_core_wire_artefact_endpoints_exist_on_card_payload():
    manifest = core_manifest()
    card_fields = set(manifest["agent_card_payload_schema"]["properties"])
    for artefact in manifest["wire_artefacts"]:
        assert artefact["endpoint_field"] in card_fields, artefact["name"]


def test_on_device_primitives_are_not_wire_artefacts():
    """CCC-2 and the sibling-annotation rule keep these off the wire."""
    names = {a["name"] for a in core_manifest()["wire_artefacts"]}
    assert names.isdisjoint(
        {"ConsentCapacityCheck", "PACEConsentAnnotation", "ActiveChallenge"}
    )


ALL_LEVELS = {
    level["level"]
    for build in (core_manifest, augmentation_manifest)
    for level in build()["conformance"]
}


@pytest.mark.parametrize("build", [core_manifest, augmentation_manifest])
def test_every_invariant_has_a_conformance_level(build):
    manifest = build()
    declared = [invariant_id(inv) for inv in manifest["invariants"]]
    assert len(declared) == len(set(declared)), "duplicate invariant IDs"
    assigned = {i for level in manifest["conformance"] for i in level["invariants"]}
    assert set(declared) == assigned, (
        f"unassigned: {sorted(set(declared) - assigned)}; unknown: {sorted(assigned - set(declared))}"
    )


@pytest.mark.parametrize("build", [core_manifest, augmentation_manifest])
def test_conformance_levels_are_well_formed(build):
    for level in build()["conformance"]:
        assert set(level["includes"]) <= ALL_LEVELS, level["level"]
        assert len(level["invariants"]) == len(set(level["invariants"])), level["level"]
        assert set(level.get("notes", {})) <= set(level["invariants"]), level["level"]


def test_only_aic_1_is_split_across_levels():
    """Each core invariant has one owner, except AIC-1: an agent keeps her
    windows, the orchestrator keeps the daily count across agents."""
    agent, orchestrator = core_manifest()["conformance"]
    assert set(agent["invariants"]) & set(orchestrator["invariants"]) == {"AIC-1"}
    assert "AIC-1" in agent["notes"] and "AIC-1" in orchestrator["notes"]
