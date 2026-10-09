# Changelog

All notable changes to PACE are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/). PACE is a
draft protocol: until 1.0.0, minor versions may change the wire format.

## [Unreleased]

### Added

- `AugmentationProfile` extension
  (`https://ravikiran438.github.io/sauvidya-pace/extensions/augmentation-profile/v1`)
  with invariants AUG-1 to AUG-6, Pydantic types, validators, MCP tools
  and a TLA+ model.
- AUG-6 task-scoped step-up: the principal takes one axis back for one
  task with a `StepUpEvent`. Agents stay off that axis in that task
  until the task ends or the principal ends the step-up; passing
  `expires_at` only makes a nudge due. New validators
  `check_step_up`, `check_step_up_grant`, `check_step_up_nudge` and
  MCP tools `validate_step_up`, `check_step_up_nudge`.
- `AccessibilityServiceRef`, the AgentCard descriptor for
  `capabilities.extensions[]`.
- Sibling primitives `PACEConsentAnnotation`, `ActiveChallenge`,
  `CCCTrend` (with the non-normative `derive_ccc_trend`) and
  `PACEViolationNotice`, each with an MCP validator.
- AG-UI binding (`pace.ag_ui`): the capability envelope as a
  `STATE_SNAPSHOT`, an active ConsentCapacityCheck as an interrupt, and
  a typed resume back to `ActiveChallenge`.
- `pace.manifest`: generates `v1/manifest.json`, the augmentation-profile
  manifest and both `SPEC.md` files
  (`uv run python -m pace.manifest --write`), with a drift test.
- Core manifest declares its wire artefacts
  (`PrincipalCapabilityProfile`, `AdaptiveInteractionContract`,
  `PACEViolationNotice`) and lists all 15 invariants.
- `specification/Pace-CrossOrchestrator.cfg`: model-checks violation
  notices between two orchestrators (8,249,080 distinct states).
- `AugmentationProfile-Liveness.cfg`: checks that an expired step-up
  always leads to a nudge or to the step-up ending.

### Changed

- **Breaking:** PACE consent metadata moves from an embedded
  `ConsentRecord.pace` block to the sibling `PACEConsentAnnotation`,
  referenced by `consent_record_id`. See §4.1 of the paper for the
  migration.
- **Breaking:** `AugmentationProfile` requires `version`, and
  `AugmentationAction` requires `profile_version`. Audits judge each
  action against the profile version it was taken under.
- TLA+ V-3 (scope) requires an exact AIC version match.
- Tooling moves to uv and Python 3.14 (`uv_build` backend, `uv.lock`,
  dev dependency group in place of the `test` extra).
- MCP server targets MCP Python SDK 2.x (`mcp>=2.3,<3`).
- Manifests report protocol version 0.1.0, tracking the package version.
- README and module headers state exactly which properties TLC checks
  (five state invariants in `Pace.tla`) and which are action guards,
  validators or API-shape properties.

### Fixed

- MCP server failed to start on fresh installs once MCP SDK 2.x removed
  the decorator API.
- AUG-4 (Skill Maintenance) flagged a legal history: help given while an
  axis was `compensate` became a violation after the principal later
  re-declared it `preserve`. Found by TLC; actions now record the axis
  kind and profile version in force.
- Augmentation-profile extension URI in code pointed at
  `github.com/...`, where no manifest is served; it now matches the
  published `github.io` URI.
- Augmentation-profile manifest listed invariants as AP-1 to AP-3; it
  now lists AUG-1 to AUG-6, matching the code and the TLA+ model.

## [0.1.0] - 2026-04-20

### Added

- PACE specification: `PrincipalCapabilityProfile`,
  `InteractionModality`, `ConsentCapacityCheck` and
  `AdaptiveInteractionContract`, with Pydantic types and runtime
  validators.
- TLA+ model `specification/Pace.tla` with TLC configuration.
- Extension URI `https://ravikiran438.github.io/sauvidya-pace/v1`.
- Reference MCP server (`pace-mcp`) exposing the validators as tools.
- Paper: [doi:10.5281/zenodo.19633138](https://doi.org/10.5281/zenodo.19633138).

[Unreleased]: https://github.com/ravikiran438/sauvidya-pace/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ravikiran438/sauvidya-pace/releases/tag/v0.1.0
