# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Build the published ExtensionManifests and their SPEC.md renderings.

Single source of truth for ``v1/manifest.json``,
``extensions/augmentation-profile/v1/manifest.json`` and the SPEC.md next
to each. The manifest envelope follows the A2A ExtensionManifest
convention (``manifest_version`` 1.0.0), so any manifest-aware validator
can check an AgentCard's PACE entry and the runtime artefacts it
exchanges without PACE-specific code.

Regenerate after changing a model, an endpoint, or an invariant::

    uv run python -m pace.manifest --write

``tests/test_manifests.py`` fails when the committed files drift from
what this module produces.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from pace import __version__
from pace.extensions.augmentation_profile import EXTENSION_URI as AUGMENTATION_URI
from pace.types import (
    PACE_EXTENSION_URI,
    AccessibilityServiceRef,
    AdaptiveInteractionContract,
    GuardianNotification,
    PACEViolationNotice,
    PrincipalCapabilityProfile,
)

MANIFEST_ENVELOPE_VERSION = "1.0.0"
PUBLISHER = "Ravi Kiran Kadaboina"
PAPER_URL = "https://doi.org/10.5281/zenodo.19633138"

CORE_INVARIANTS: tuple[str, ...] = (
    "PCP-1: the PrincipalCapabilityProfile is stored on-device; no remote agent may write or modify it.",
    "PCP-2: PCP versions are immutable and append-only; corrections are new versions.",
    "PCP-3: a guardian declaring a PCP MUST be verifiably identified.",
    "IM-1: an InteractionModality MUST be computed from the PCP before any interaction; an agent that cannot satisfy adaptations_required MUST escalate instead.",
    "IM-2: an agent MUST use a language the PCP pins (adaptations_required language:<code>) or, without a pin, one listed at or above the AIC's min_language_fluency; otherwise it routes to a capable sub-agent or escalates, and never falls back to another language. An AIC MUST NOT bind a language the PCP rules out.",
    "CCC-1: a ConsentCapacityCheck MUST precede any consent record for principals whose decision_capacity is fluctuating, limited, or guardian_required.",
    "CCC-2: ConsentCapacityCheck results MUST NOT be transmitted to any remote agent.",
    "CCC-3: a ConsentCapacityCheck is not a clinical assessment.",
    "CCC-4: relay carries the question, not the consent: consent reached through a guardian relay requires a ConsentCapacityCheck of the principal that is not guardian_confirmed, unless decision_capacity is guardian_required.",
    "AIC-1: no interaction outside valid_time_windows unless classified as emergency. Windows and the sundown block are the principal's local times in interaction_rules.timezone, whatever clock the agent runs on.",
    "AIC-2: no more than max_options_per_turn options in a single turn.",
    "AIC-3: after an unanswered attempt, no retry in the same window (non_response_policy.retry_delay = next_window); after non_response_policy.escalate_after non-responses the agent escalates to the guardian instead of trying again. escalate_after may not exceed max_retries + 1, so a principal is never dropped silently.",
    "AIC-4: contract violations trigger the declared violation_policy; notify_guardian sends a GuardianNotification with both clocks and no capacity data, and cross-orchestrator blocks travel as signed PACEViolationNotice records.",
    "AIC-5: an InteractionModality stays within the contract it was computed under: the contract's language, a timeout at least as long, speech no faster, no more options, no denser information, the required confirmation style and memory recap.",
    "V-1: a receiver bound by the same aic_version for the principal MUST block offending_agent_id for at least block_duration_seconds.",
    "V-2: receivers MUST NOT forward a PACEViolationNotice (one-hop broadcast).",
    "V-3: receivers without an AIC for the principal log the notice but MUST NOT apply the block.",
)

AUGMENTATION_INVARIANTS: tuple[str, ...] = (
    "AUG-1 Reversibility: every augmentation can be reverted; after an AxisRevertedEvent no compensate or amplify action may target that axis.",
    "AUG-2 Audit Decomposition: every AugmentationAction records its mediation.",
    "AUG-3 Identity Preservation: actions that alter the principal's voice or written style require identity_consent.",
    "AUG-4 Skill Maintenance: no agent compensate or amplify action on an axis declared preserve in the profile version the action was taken under; re-declaring an axis governs later actions only.",
    "AUG-5 Emergency Boundary: an emergency trigger forces a human handoff; no compensate or amplify action until a human acknowledges it.",
    "AUG-6 Task-Scoped Step-Up: only the principal may take an axis back for one task; agents stay off that axis in that task until the task ends or the principal ends the step-up. Passing expires_at only makes a nudge due; it never resumes help.",
)


def _artefact(
    name: str, description: str, endpoint_field: str, method: str, model: type[BaseModel]
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "endpoint_field": endpoint_field,
        "method": method,
        "schema": model.model_json_schema(),
    }


def core_manifest() -> dict[str, Any]:
    """ExtensionManifest for the PACE core extension (``/v1``)."""
    return {
        "manifest_version": MANIFEST_ENVELOPE_VERSION,
        "extension": {
            "uri": PACE_EXTENSION_URI,
            "name": "Sauvidya PACE Framework",
            "description": "Principal accessibility / capacity / engagement layer for A2A orchestrators.",
            "version": __version__,
            "publisher": PUBLISHER,
            "human_readable_spec": PAPER_URL,
        },
        "agent_card_payload_schema": AccessibilityServiceRef.model_json_schema(),
        "wire_artefacts": [
            _artefact(
                "PrincipalCapabilityProfile",
                "Read-only PCP copy the principal's PACE orchestrator delivers to an agent before it may interact (PCP-1, IM-1).",
                "pcp_endpoint",
                "POST",
                PrincipalCapabilityProfile,
            ),
            _artefact(
                "AdaptiveInteractionContract",
                "The orchestrator's currently bound AIC for a principal; the URL carries a {principal_id} placeholder.",
                "aic_endpoint",
                "GET",
                AdaptiveInteractionContract,
            ),
            _artefact(
                "GuardianNotification",
                "What the guardian receives when the contract's policy says notify_guardian (AIC-4): the agent, the rule, a plain-language summary, both clocks, the actions taken and the next allowed contact. Carries no capacity data (CCC-2).",
                "guardian_escalation_endpoint",
                "POST",
                GuardianNotification,
            ),
            _artefact(
                "PACEViolationNotice",
                "Signed one-hop broadcast of an AIC violation to peer orchestrators (V-1, V-2, V-3).",
                "violation_notice_endpoint",
                "POST",
                PACEViolationNotice,
            ),
        ],
        "invariants": list(CORE_INVARIANTS),
    }


def augmentation_manifest() -> dict[str, Any]:
    """ExtensionManifest for the augmentation-profile sub-extension."""
    return {
        "manifest_version": MANIFEST_ENVELOPE_VERSION,
        "extension": {
            "uri": AUGMENTATION_URI,
            "name": "PACE Augmentation-Profile Extension",
            "description": "Active augmentation actions for principals, with reversibility and identity-preservation guarantees.",
            "version": __version__,
            "publisher": PUBLISHER,
        },
        "agent_card_payload_schema": {
            "type": "object",
            "title": "OpaquePayload",
            "description": (
                "This extension declares itself by URI presence and does "
                "not constrain the AgentCard payload. Validators accept "
                "any object."
            ),
            "additionalProperties": True,
        },
        "wire_artefacts": [],
        "invariants": list(AUGMENTATION_INVARIANTS),
    }


def render_spec_md(manifest: dict[str, Any], manifest_path: str) -> str:
    """Render a manifest as the developer-facing SPEC.md next to it."""
    ext = manifest["extension"]
    lines = [
        f"# {ext['name']} — Wire Specification",
        "",
        f"> Generated from `{manifest_path}` by `uv run python -m pace.manifest --write`. Do not hand-edit.",
        "",
        f"- **Extension URI:** `{ext['uri']}`",
        f"- **Protocol version:** {ext['version']} (draft)",
        f"- **Manifest envelope version:** {manifest['manifest_version']}",
        f"- **Publisher:** {ext['publisher']}",
    ]
    if ext.get("human_readable_spec"):
        lines.append(f"- **Paper / human-readable spec:** {ext['human_readable_spec']}")
    lines += ["", ext["description"], "", "## AgentCard payload", ""]

    schema = manifest["agent_card_payload_schema"]
    if schema.get("title") == "OpaquePayload":
        lines.append(
            "This extension declares itself by URI presence and does not "
            "constrain the AgentCard payload. Validators accept any object "
            "in the entry's `params`."
        )
    else:
        required = set(schema.get("required", []))
        lines += [
            "**Required fields:** " + ", ".join(f"`{r}`" for r in sorted(required)),
            "",
            "| Field | Type | Required | Notes |",
            "|---|---|---|---|",
        ]
        for name, prop in sorted(schema.get("properties", {}).items()):
            notes = " ".join((prop.get("description") or "").split())
            lines.append(
                f"| `{name}` | {_type_label(prop)} | {'yes' if name in required else 'no'} | {notes} |"
            )
    lines.append("")

    if manifest["wire_artefacts"]:
        lines += ["## Wire artefacts", ""]
        for art in manifest["wire_artefacts"]:
            lines += [
                f"### `{art['name']}`",
                "",
                art["description"],
                "",
                f"Delivered via `{art['method']}` to the URL in `{art['endpoint_field']}`. "
                "Body schema: the `schema` field of this artefact in the manifest.",
                "",
            ]

    lines += ["## Invariants", ""]
    lines += [f"- {inv}" for inv in manifest["invariants"]]
    lines.append("")
    return "\n".join(lines)


def _type_label(prop: dict[str, Any]) -> str:
    if "anyOf" in prop:
        return " or ".join(_type_label(p) for p in prop["anyOf"])
    if "$ref" in prop:
        return prop["$ref"].rsplit("/", 1)[-1]
    kind = prop.get("type", "any")
    if kind == "array":
        return f"array<{_type_label(prop.get('items', {}))}>"
    return kind


def render_json(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def outputs(root: Path) -> dict[Path, str]:
    """Every generated file, keyed by its path under ``root``."""
    files: dict[Path, str] = {}
    for rel_dir, manifest in (
        ("v1", core_manifest()),
        ("extensions/augmentation-profile/v1", augmentation_manifest()),
    ):
        manifest_rel = f"{rel_dir}/manifest.json"
        files[root / manifest_rel] = render_json(manifest)
        files[root / rel_dir / "SPEC.md"] = render_spec_md(manifest, manifest_rel)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Write the generated files.")
    mode.add_argument("--check", action="store_true", help="Exit 1 if committed files drift.")
    args = parser.parse_args(argv)

    stale = []
    for path, content in outputs(args.root).items():
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path.relative_to(args.root)}")
        elif not path.exists() or path.read_text(encoding="utf-8") != content:
            stale.append(str(path.relative_to(args.root)))
    if stale:
        print("out of date: " + ", ".join(stale), file=sys.stderr)
        print("run: uv run python -m pace.manifest --write", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
