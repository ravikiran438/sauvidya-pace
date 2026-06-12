# Sauvidya PACE Framework — Wire Specification

> Generated from `v1/manifest.json`. Re-render after the manifest changes; do not hand-edit.

- **Extension URI:** `https://ravikiran438.github.io/sauvidya-pace/v1`
- **Protocol version:** 1.0.0
- **Manifest envelope version:** 1.0.0
- **Publisher:** Ravi Kiran Kadaboina
- **Paper / human-readable spec:** https://doi.org/10.5281/zenodo.19633138

Principal accessibility / capacity / engagement layer for A2A orchestrators.

## AgentCard payload

**Required fields:** `aic_endpoint`, `pcp_endpoint`, `supported_languages`, `supported_modalities`, `version`, `violation_notice_endpoint`

| Field | Type | Required | Notes |
|---|---|---|---|
| `aic_endpoint` | string | yes | HTTPS URL pattern (with ``{principal_id}`` placeholder) where the AdaptiveInteractionContract for a given principal is fetched. Returns the orchestrator's currently bound AIC. |
| `guardian_escalation_endpoint` | any | no | HTTPS URL the agent uses to escalate to a registered guardian. REQUIRED when the agent serves principals whose PCP indicates guardian_required decision_capacity. |
| `pcp_endpoint` | string | yes | HTTPS URL where this agent exchanges PrincipalCapabilityProfile (PCP) metadata with the principal's PACE orchestrator. The endpoint MUST authenticate the orchestrator; PCPs are never fetched by remote A2A agents. |
| `supported_languages` | array<string> | yes | ISO 639-1 codes this agent can converse in. Used to fail fast when an AIC requires a language the agent cannot speak. |
| `supported_modalities` | array<string> | yes | PrimaryChannel values this agent can drive (e.g. ['voice', 'large_text', 'simple_visual']). Validators cross-check this against InteractionModality.modality_plan.primary_channel. |
| `supports_active_assessment` | boolean | no | True if this agent implements active ConsentCapacityCheck (challenge-response). False means it falls back to passive interpolation only. |
| `version` | string | yes | PACE protocol semver this agent implements. |
| `violation_notice_endpoint` | string | yes | HTTPS URL where peer orchestrators POST PACEViolationNotice messages targeting this agent. REQUIRED so the violation broadcast loop has a destination per orchestrator. |

## Invariants

- IM-1: InteractionModality MUST be computed from PCP before any interaction.
- CCC-2: capacity_signal MUST NOT be transmitted to remote agents.
- AIC-1: no interaction outside valid_time_windows unless emergency.

---

_Drift between this `SPEC.md` and the protocol's pydantic models indicates the manifest needs regenerating. CI may compare a freshly-rendered version against the committed one._
