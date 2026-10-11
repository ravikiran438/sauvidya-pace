# Decisions

One line per decision: the rule, then the fact or measurement behind it.
No number means the line says **Belief.** Reversed decisions are struck
through and kept, with the replacement under them. A decision that is not
in this file was not made.

## Thesis

- Accessibility for agents belongs at the protocol layer (what the agent
  says, when, in which language, with how many choices, whether consent is
  real now), not the rendering layer. **Belief.** See
  [ADR 001](../adrs/001-accessibility-as-protocol-not-rendering.md). The
  baseline gate in [CHECKPOINTS.md](../CHECKPOINTS.md) exists to turn this
  into a number.

## Shape of the protocol

- PACE ships as an A2A `capabilities.extensions[]` entry and an MCP
  capability, not a core spec change. Adoption needs no upstream approval.
- On-device data never travels: capacity checks, consent annotations and
  active-challenge evidence are not wire artefacts. Enforced by
  `test_on_device_primitives_are_not_wire_artefacts`.
- Wire artefacts are declared in the manifest with their endpoints:
  `PrincipalCapabilityProfile` (POST `pcp_endpoint`),
  `AdaptiveInteractionContract` (GET `aic_endpoint`), `PACEViolationNotice`
  (POST `violation_notice_endpoint`). The a2a-testbed manifest validator
  only checks traffic it is told about; the manifest had none (2026-10-09).
- The manifests and their SPEC.md are generated from the code
  (`pace.manifest`) and a test fails on drift. The hand-maintained ones
  said protocol 1.0.0 while the package said 0.1.0, and named the
  augmentation invariants AP-1..3 while the code used AUG-1..5.
- The augmentation-profile extension URI is the `github.io` one. The code
  constant pointed at `github.com/...`, where no manifest is served.
- PACE consent metadata is a sibling `PACEConsentAnnotation` referencing
  the consent record by ID, not a block inside it. Keeps Anumati's schema
  untouched and the annotation on-device (CCC-2).

## Language and consent

- ~~IM-2: the modality's language must be listed in the PCP.~~ Struck
  2026-10-09: the paper's own example (English at 0.3, `language:te`
  required) passed.
  - IM-2: a `language:<code>` pin wins; otherwise the language must be
    listed at or above `min_language_fluency`. The paper's example is now
    rejected, with the next step in the error.
- `min_language_fluency` defaults to 0.7 and lives in the AIC, set by the
  guardian. **Belief.** Chosen to match the CCC "proceed" threshold.
- A contract may not bind a language the PCP rules out. A guardian can
  approve a contract by mistake or in bad faith (paper §8). **Belief**
  that this is the likely failure; no incidents measured.
- When no agent speaks an acceptable language: a capable sub-agent, then
  another acceptable language (only without a pin), then guardian relay,
  then defer. Never fall back. **Belief.**
- CCC-4, relay carries the question, not the consent: a relayed consent
  needs a capacity check of the principal that is not `guardian_confirmed`,
  except for `guardian_required` principals. Without it, a language gap is
  a path for the guardian to consent on her behalf (paper §8).
- Only the principal may step up (AUG-6). A guardian stepping her up
  would withhold help on her behalf. **Belief.**

## Time

- The contract carries the principal's IANA time zone
  (`interaction_rules.timezone`, required); windows and the sundown block
  are her local times. An agent in Texas at 08:30 CDT was judged as 08:30,
  not as her 19:00 (perturbation 16).
- Time checks take a zone-aware timestamp and reject naive ones. A bare
  `HH:MM` cannot say whose clock it was read from.
- Daylight saving comes from the IANA zone database. US DST shifts the
  guardian's clock against hers by an hour twice a year; India has none.
- `tzdata` is a dependency on Windows only: 2.7 MB installed, and macOS and
  Linux ship the zone database.
- `max_interactions_per_day` counts per principal, across all agents, by
  her local calendar day. Three agents calling once each are three calls
  to her; a UTC day would reset at 05:30 her time. Decided 2026-10-10;
  enforcement in CP2.

## The contract and the agent's plan

- AIC-5: an InteractionModality stays within the contract it was computed
  under. Each primitive validated alone; a 60 s plan under a 300 s
  contract passed every check (perturbation 17).
- The checks are one-directional: an agent may wait longer, speak slower,
  offer fewer options and carry less information than the contract
  allows, never more. Language and confirmation style must match. A
  recap is required when the contract asks for one. **Belief** that every
  dimension is monotone this way; per-person feedback may show otherwise.
- AIC-5 reports every violation at once, as data (`problems`), so an agent
  developer fixes the plan in one pass.
- The CP2 gate is measured by `scripts/contract-readers.py`, a text search
  over the reader modules. It can over-count readers (a name used for
  something else), never under-count. A hand count was off by one.

## Augmentation profile

- ~~An axis kind can change freely and AUG-4 checks actions against the
  current kind.~~ Struck 2026-10-09: TLC found a legal history violating
  AUG-4 in 4 steps (help given under `compensate`, axis re-declared
  `preserve`).
  - Each action records the axis kind and profile version in force;
    profiles are versioned and append-only.
- Step-up is scoped to one task, not the profile. "Let me do this one
  myself" is a decision about one task; help returns when it ends.
  **Belief.**
- ~~Considered: a one-way autonomy ratchet.~~ Rejected 2026-10-09: it
  strands principals whose capability declines.
- ~~A step-up expires at its time limit.~~ Struck 2026-10-09: expiry
  mid-task lets the agent take over from someone writing slowly.
  - Passing `expires_at` only makes a nudge due; help resumes when the
    task ends or the principal ends the step-up. TLC: `StepUpRespected`
    holds, and removing the guard is caught.

## Privacy and evidence

- ~~ActiveChallenge digests are SHA-256 of the canonical text.~~ Struck
  2026-10-09: responses to a capacity check are a dozen likely words, so a
  dictionary of plain hashes recovers them without the transcript.
  - HMAC-SHA256 under an on-device audit key, with `digest_key_id`.
- ~~Considered: salted hashes.~~ Rejected: the salt is stored with the
  record, so hashing "yes" + salt still recovers short answers. Only a
  secret helps.
- Both digests cover `challenge_id` and a versioned role label, so a "yes"
  cannot be copied into another record or swapped between challenge and
  response.
- `PACEViolationNotice.evidence_hash` stays plain SHA-256: it covers only
  fields the notice already carries in the clear.

## Verification and testing

- TLC checks 5 state invariants in `Pace.tla`; AIC-1, V-2 and V-3 are
  action guards. The README claimed 6 verified properties.
- Two core configs: one orchestrator (40,760 states) and two
  (8,249,080 states). With one orchestrator the issuer and receiver of a
  violation notice are the same party. Three agents: past 17M states
  after 2.5 minutes, not tractable for CI.
- The augmentation audit log is modeled as a set, and user-direct actions
  are not recorded. As a sequence the model passed 22M states without
  finishing, and the set alone still passed 20M; with both changes it
  finishes at 4,048,527. No invariant reads order or user-direct records.
- Every model check runs from `scripts/check-models.sh`, with reachability
  witnesses (non-vacuity) and mutants TLC must catch.
- TLC search depth is not reported: it varied 17 vs 18 between runs with
  parallel workers. Distinct-state counts are stable.

## Tooling and release

- uv and Python 3.14 (latest stable as of 2026-10-09); the build backend
  is `uv_build`.
- MCP SDK 2.x. Fresh installs of the `[mcp]` extra failed to start under
  1.x decorators once 2.x shipped.
- Git installs point at `main` until v0.2.0 is tagged: the v0.1.0 tag
  installs a server that fails on MCP SDK 2.x.
- The next release is 0.2.0: Unreleased contains wire-breaking changes.

## Reference defaults

All guardian-configurable, from the paper's companion implementation.
None has been measured with real principals.

- Capacity thresholds 0.7 / 0.4 / 0.2 (proceed / simplify / defer /
  escalate). **Belief.**
- `max_options_per_turn` 2, `response_timeout_seconds` 300,
  `speech_rate` 0.7, `max_interactions_per_day` 3. **Belief.**
- CCC trend: OLS slope over 30 days, ±0.005 noise floor, 5-sample
  minimum. **Belief.**
