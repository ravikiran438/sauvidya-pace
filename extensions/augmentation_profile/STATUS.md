# Augmentation Profile: Status

**Stage:** Reference implementation
**Extension URI:** https://github.com/ravikiran438/sauvidya-pace/extensions/augmentation-profile/v1
**First drafted:** 2026-04-25
**Depends on:** PACE Core v0.1+
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

This extension adds an active-augmentation primitive and five safety
invariants (AUG-1 through AUG-5) to PACE. PACE Core gives agents a
*defensive* contract for accommodating principal capacity. This
extension adds an *offensive* contract for replacing missing capacity,
amplifying existing strengths, and preserving capacities that must
not atrophy.

## Primitives this extension adds

- `AugmentationAxis`: a single named dimension with kind (`compensate`,
  `amplify`, `preserve`)
- `AugmentationProfile`: per-principal declaration with reversibility,
  audit, identity, skill-maintenance, and emergency rules
- `AugmentationAction`: a logged action with `mediation` field
- `EmergencyTrigger`: declared crisis condition forcing handoff

## Invariants this extension adds

- **AUG-1 Reversibility**: revertible by principal; typed event
- **AUG-2 Audit Decomposition**: every action records its mediation
- **AUG-3 Identity Preservation**: explicit consent for voice/style
- **AUG-4 Skill Maintenance**: `preserve` axes are never replaced
- **AUG-5 Emergency Boundary**: triggers force handoff

## Interop points with PACE Core

- `PrincipalCapabilityProfile` (PCP) is the static capacity declaration;
  `AugmentationProfile` references it via `pcp_version`
- `AdaptiveInteractionContract` (AIC) governs interaction-time rules;
  this extension operates at the action level, one layer above
- IM-1/IM-2/CCC-1/CCC-2/AIC-* invariants are unchanged
- A profile change MUST also update `pcp_version` if it implies a new
  capacity statement

## What exists today

- TLA+ specification of AUG-1..AUG-5 under `AugmentationProfile.tla`.
  Reversibility and EmergencyBoundary use snapshot fields
  (`axis_reverted_at_append`, `handed_off_at_append`) on each action
  record so the invariants check state-at-action-time rather than
  the current monotonically-growing state.
- TLC configuration for a small model (2 principals × 3 axes × 2 triggers).
  **TLC has not been run against this configuration yet**; the spec
  is offered for review and as a static artifact. A model-check pass
  with output captured here is open work.
- Pydantic types for the four new primitives
- Runtime validators for the five invariants
- Test suite covering the invariants

## What is open

- Population-specific augmentation taxonomies (elderly care, BCI users,
  autistic users) — application-layer concerns
- Composition with Phala `welfare_detectors`: capacity-conditioned
  welfare detector activation (which detector_types apply at which
  capacity profile)
- Empirical study on skill-atrophy rates with vs without AUG-4
  enforcement
- Reference profiles for common deployments

## Not in scope

- Specific augmentation algorithms (BCI signal interpretation, social
  cue decoders, executive-function scaffolds) — those are agent-local
- Hardware-side augmentation (BCI device calibration, sensor fusion)
- Therapeutic recommendations (these are clinical, not protocol)

## Feedback

Open an issue or PR on the parent repository. Reference the extension
in the title: `[augmentation-profile] <your topic>`.
