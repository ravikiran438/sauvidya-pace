# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Drift guard: committed manifests and SPEC.md files match the generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from pace import __version__
from pace.manifest import augmentation_manifest, core_manifest, outputs

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
