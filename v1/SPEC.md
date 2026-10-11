# Sauvidya PACE Framework — Wire Specification

> Generated from `v1/manifest.json` by `uv run python -m pace.manifest --write`. Do not hand-edit.

- **Extension URI:** `https://ravikiran438.github.io/sauvidya-pace/v1`
- **Protocol version:** 0.1.0 (draft)
- **Manifest envelope version:** 1.0.0
- **Publisher:** Ravi Kiran Kadaboina
- **Paper / human-readable spec:** https://doi.org/10.5281/zenodo.19633138

Principal accessibility / capacity / engagement layer for A2A orchestrators.

## AgentCard payload

**Required fields:** `aic_endpoint`, `pcp_endpoint`, `supported_languages`, `supported_modalities`, `version`, `violation_notice_endpoint`

| Field | Type | Required | Notes |
|---|---|---|---|
| `aic_endpoint` | string | yes | HTTPS URL pattern (with ``{principal_id}`` placeholder) where the AdaptiveInteractionContract for a given principal is fetched. Returns the orchestrator's currently bound AIC. |
| `guardian_escalation_endpoint` | string or null | no | HTTPS URL the agent uses to escalate to a registered guardian. REQUIRED when the agent serves principals whose PCP indicates guardian_required decision_capacity. |
| `pcp_endpoint` | string | yes | HTTPS URL where this agent exchanges PrincipalCapabilityProfile (PCP) metadata with the principal's PACE orchestrator. The endpoint MUST authenticate the orchestrator; PCPs are never fetched by remote A2A agents. |
| `supported_languages` | array<string> | yes | ISO 639-1 codes this agent can converse in. Used to fail fast when an AIC requires a language the agent cannot speak. |
| `supported_modalities` | array<string> | yes | PrimaryChannel values this agent can drive (e.g. ['voice', 'large_text', 'simple_visual']). Validators cross-check this against InteractionModality.modality_plan.primary_channel. |
| `supports_active_assessment` | boolean | no | True if this agent implements active ConsentCapacityCheck (challenge-response). False means it falls back to passive interpolation only. |
| `version` | string | yes | PACE protocol semver this agent implements. |
| `violation_notice_endpoint` | string | yes | HTTPS URL where peer orchestrators POST PACEViolationNotice messages targeting this agent. REQUIRED so the violation broadcast loop has a destination per orchestrator. |

## Wire artefacts

### `PrincipalCapabilityProfile`

Read-only PCP copy the principal's PACE orchestrator delivers to an agent before it may interact (PCP-1, IM-1).

Delivered via `POST` to the URL in `pcp_endpoint`. Body schema: the `schema` field of this artefact in the manifest.

### `AdaptiveInteractionContract`

The orchestrator's currently bound AIC for a principal; the URL carries a {principal_id} placeholder.

Delivered via `GET` to the URL in `aic_endpoint`. Body schema: the `schema` field of this artefact in the manifest.

### `GuardianNotification`

What the guardian receives when the contract's policy says notify_guardian (AIC-4): the agent, the rule, a plain-language summary, both clocks, the actions taken and the next allowed contact. Carries no capacity data (CCC-2).

Delivered via `POST` to the URL in `guardian_escalation_endpoint`. Body schema: the `schema` field of this artefact in the manifest.

### `PACEViolationNotice`

Signed one-hop broadcast of an AIC violation to peer orchestrators (V-1, V-2, V-3).

Delivered via `POST` to the URL in `violation_notice_endpoint`. Body schema: the `schema` field of this artefact in the manifest.

## Invariants

- PCP-1: the PrincipalCapabilityProfile is stored on-device; no remote agent may write or modify it.
- PCP-2: PCP versions are immutable and append-only; corrections are new versions.
- PCP-3: a guardian declaring a PCP MUST be verifiably identified.
- IM-1: an InteractionModality MUST be computed from the PCP before any interaction; an agent that cannot satisfy adaptations_required MUST escalate instead.
- IM-2: an agent MUST use a language the PCP pins (adaptations_required language:<code>) or, without a pin, one listed at or above the AIC's min_language_fluency; otherwise it routes to a capable sub-agent or escalates, and never falls back to another language. An AIC MUST NOT bind a language the PCP rules out.
- CCC-1: a ConsentCapacityCheck MUST precede any consent record for principals whose decision_capacity is fluctuating, limited, or guardian_required.
- CCC-2: ConsentCapacityCheck results MUST NOT be transmitted to any remote agent.
- CCC-3: a ConsentCapacityCheck is not a clinical assessment.
- CCC-4: relay carries the question, not the consent: consent reached through a guardian relay requires a ConsentCapacityCheck of the principal that is not guardian_confirmed, unless decision_capacity is guardian_required.
- AIC-1: no interaction outside valid_time_windows unless classified as emergency. Windows and the sundown block are the principal's local times in interaction_rules.timezone, whatever clock the agent runs on.
- AIC-2: no more than max_options_per_turn options in a single turn.
- AIC-3: after a response timeout, no immediate retry; escalate after repeated non-responses. Not yet implemented in this reference (no non_response_policy on the contract).
- AIC-4: contract violations trigger the declared violation_policy; notify_guardian sends a GuardianNotification with both clocks and no capacity data, and cross-orchestrator blocks travel as signed PACEViolationNotice records.
- AIC-5: an InteractionModality stays within the contract it was computed under: the contract's language, a timeout at least as long, speech no faster, no more options, no denser information, the required confirmation style and memory recap.
- V-1: a receiver bound by the same aic_version for the principal MUST block offending_agent_id for at least block_duration_seconds.
- V-2: receivers MUST NOT forward a PACEViolationNotice (one-hop broadcast).
- V-3: receivers without an AIC for the principal log the notice but MUST NOT apply the block.
