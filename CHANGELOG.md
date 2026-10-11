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
- Conformance levels: PACE Agent, PACE Orchestrator (includes Agent) and
  PACE Augmentation (includes Agent), declared under `conformance` in
  both manifests and rendered in each `SPEC.md`. A test fails if an
  invariant has no level or a level names an unknown invariant.
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
- CI (GitHub Actions, pinned by commit SHA): tests, manifest drift
  check and MCP self-check on Python 3.14, plus every TLA+ model.
- `scripts/check-models.sh`: runs all TLC configs, reachability
  witnesses (`AugmentationProfileWitness.tla`) and mutants that TLC must
  catch, with a pinned, checksum-verified `tla2tools.jar`.
- AIC-5 `validate_modality_contract`: an InteractionModality must stay
  within its contract (language, timeout, speech rate, options,
  information density, confirmation style, memory recap), reporting every
  violation. MCP tool `validate_modality_contract`.
- AIC-3 `NonResponsePolicy` (`max_retries`, `retry_delay: next_window`,
  `escalate_after`) on the contract, and `validate_retry`: no retry in
  the window of an unanswered attempt; escalate to the guardian after
  `escalate_after` non-responses. `escalate_after` may not exceed
  `max_retries + 1`, so a principal is never dropped silently. MCP tool
  `validate_retry`.
- `scripts/contract-readers.py` also reports contract fields the paper
  names but the code does not define.
- IM-1 `validate_channels`: every channel of a modality, primary and
  fallback, must reach the principal (no voice if she cannot hear, no
  text if she cannot see or read), be supported by the agent, and the
  chain must end in `guardian_relay` or an escalation target. MCP tool
  `validate_channels`.
- CI runs `scripts/contract-readers.py`.
- AIC-1 daily limit: `validate_daily_limit` and
  `interactions_remaining` count every contact per principal, across all
  agents, by her local calendar day; emergencies are never blocked but
  are counted. MCP tool `validate_daily_limit`.
- AIC-4 `enforce_violation`: applies the contract's violation policy and
  returns the actions, whether to broadcast a block, and a
  `GuardianNotification` (plain-language summary, both clocks, actions
  taken, next allowed contact, no capacity data). New wire artefact,
  POSTed to `guardian_escalation_endpoint`. MCP tool `enforce_violation`.
- `scripts/contract-readers.py`: counts contract fields that no validator,
  binding or tool reads.
- `InteractionRules.min_language_fluency` (default 0.7, guardian
  configurable) and `acceptable_languages()`, which implement the IM-2
  language rule.
- `validate_contract_language`: an AIC may not bind every agent to a
  language the PCP rules out. MCP tool `validate_contract_language`.
- CCC-4, relay carries the question, not the consent:
  `PACEConsentAnnotation.relayed_by` records a guardian relay, and
  `validate_relay_consent` requires a capacity check of the principal
  that is not `guardian_confirmed`, unless `decision_capacity` is
  `guardian_required`. MCP tool `validate_relay_consent`.

### Changed

- **Breaking:** PACE consent metadata moves from an embedded
  `ConsentRecord.pace` block to the sibling `PACEConsentAnnotation`,
  referenced by `consent_record_id`. See §4.1 of the paper for the
  migration.
- **Breaking:** `InteractionRules.guardian_cc` and
  `escalation_on_confusion` removed: no reader and no story needed them.
- **Breaking:** one channel vocabulary. `FallbackEntry.channel` and
  `AccessibilityServiceRef.supported_modalities` take `PrimaryChannel`
  values (`guardian_relay` for fallbacks); `large_text` and
  `text_large_font` are no longer accepted.
- **Breaking:** `ViolationPolicy` fields are lists of `EnforcementAction`
  (the `"a + b"` string form is still accepted), with a new
  `on_modality_contract_violation`. `EnforcementAction` gains `log`;
  `ViolationType` gains `modality_contract`.
- **Breaking:** `InteractionRules.timezone` (IANA, required): time
  windows and the sundown block are the principal's local times.
  `validate_time_window` takes a zone-aware `datetime` instead of an
  `HH:MM` string and rejects naive timestamps; the MCP tool takes `at`
  with a UTC offset and reports the principal's local time. An agent in
  Texas at 08:30 CDT was judged as 08:30 rather than her 19:00 IST.
  `tzdata` is required on Windows.
- **Breaking:** `ActiveChallenge` digests are HMAC-SHA256 under an
  on-device audit key (`hmac-sha256:<hex>`), with a new required
  `digest_key_id`. Plain SHA-256 digests of short responses ("yes",
  "the insurance") could be recovered by hashing likely answers. Both
  digests also cover `challenge_id` and a role label, so a digest cannot
  be copied into another record or swapped between challenge and
  response. The
  AG-UI binding takes `audit_key` and rejects a resume whose challenge
  text no longer matches its digest.
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

- AIC-3 was in the paper and the manifest but not in the code:
  `non_response_policy` did not exist. Implemented.
- IM-2 ignored fluency and language pins: `validate_language_match`
  accepted any language listed in the PCP, so the paper's own example (an
  English call to a principal with English at 0.3 and `language:te`
  required) passed. A pin now wins; otherwise the language must meet the
  fluency floor. Errors name the next step: a sub-agent that speaks an
  acceptable language, then the escalation target.
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
