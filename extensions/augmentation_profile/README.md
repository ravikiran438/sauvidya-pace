# Augmentation Profile Extension

This extension extends the PACE specification from defensive
accommodation toward active prosthetic augmentation. PACE Core
declares a principal's capacity profile and adapts the agent's
interaction surface to it. This extension adds the missing piece: how
an agent *actively replaces* missing capacity or *amplifies* existing
strengths, while preserving reversibility, auditability, identity,
skill maintenance, and emergency handoff.

## Why this extension

PACE Core answers "what can the principal do, and how should we
accommodate that?" — a defensive question. This extension answers
"where do we compensate, where do we amplify, and what must we never
replace?" — an offensive question. Both questions apply broadly to
any agent acting on a principal's behalf, and become most acute for
principals who benefit from active prosthesis: elderly users with
cognitive decline, BCI users with motor, attentional, or affective
channels, and autistic users with sensory or social-interpretation
needs.

The risks of agent prosthesis are non-trivial. Skill atrophy is
empirically attested: habitual GPS users show measurable degradation
in cognitive-mapping ability and steeper hippocampal-spatial-memory
decline relative to controls who navigate without turn-by-turn
assistance [1]. Learned helplessness and missed-emergency risks
are well-established constructs in the clinical accommodation
literature. Identity erosion is a bioethics framing rather than a
clinical construct, but it is recurrent in the prosthesis-and-agency
literature. The six invariants below exist to make these risks
contractual rather than optional.

## What this extension adds

### Primitives

| Primitive | Purpose |
|---|---|
| `AugmentationAxis` | A single dimension of augmentation: `compensate`, `amplify`, or `preserve` |
| `AugmentationProfile` | Per-principal declaration: which axes are augmented, with what reversibility, audit, identity, skill-maintenance, and emergency rules |
| `AugmentationAction` | A logged action with a `mediation` field (`agent_compensated`, `agent_amplified`, `user_direct`, `agent_handed_off`) |
| `EmergencyTrigger` | Declared crisis condition that MUST force human handoff |
| `StepUpEvent` | The principal takes one axis back for one task (AUG-6) |

`AugmentationProfile` carries a `version`; versions are append-only.
Every `AugmentationAction` records the `profile_version` it was taken
under and, when it belongs to a task, its `task_id`.

### Invariants

| Invariant | Statement |
|---|---|
| **AUG-1 Reversibility** | Every augmentation declared in an `AugmentationProfile` MUST be revertible by the principal. Reversion MUST be a typed event recorded against the profile, not a soft toggle. |
| **AUG-2 Audit Decomposition** | Every `AugmentationAction` MUST carry a `mediation` field distinguishing agent-compensated, agent-amplified, user-direct, and agent-handed-off actions. Aggregate logs that erase this distinction violate AUG-2. |
| **AUG-3 Identity Preservation** | Any agent action that would alter the principal's voice, written style, or expressive identity (impersonation in any direction) MUST cite an `identity_consent` element in the profile. Implicit consent is forbidden. **Note:** AUG-3 is enforced against the agent's self-attestation in `AugmentationAction.alters_identity`. A misbehaving agent that lies about this flag cannot be caught by AUG-3 alone; pair it with detector provenance (Phala WD-4) for end-to-end accountability. |
| **AUG-4 Skill Maintenance** | Capacities marked `preserve` in the profile MUST NOT be replaced by `agent_compensated` or `agent_amplified` actions. The agent MAY scaffold but MUST NOT substitute. Each action is judged against the profile version it was taken under: re-declaring an axis as `preserve` governs later actions and does not make earlier help a violation. |
| **AUG-5 Emergency Boundary** | When any declared `EmergencyTrigger` fires, the agent MUST emit an `agent_handed_off` action and MUST NOT take any further compensating or amplifying action until human acknowledgment. |
| **AUG-6 Task-Scoped Step-Up** | The principal MAY take a `compensate` or `amplify` axis back for one task with a `StepUpEvent`; only the principal can grant one. While it is open, no `agent_compensated` or `agent_amplified` action may target that axis in that task. The task ending closes it. `expires_at` is a backstop for abandoned tasks: once it passes, the agent MUST nudge the principal and keep waiting. It MUST NOT resume help on its own; only the principal ending the step-up (for example, answering the nudge) or the task ending lifts the block. AUG-5 still applies during a step-up. |

### Why step-up is task-scoped

"Let me write this one myself" is a decision about one task, not a
change to the whole profile. Scoping the step-up to a task keeps the
declared profile as the default, so help returns on its own when the
task is done. That matters most for principals whose capability
declines: nobody is left without help because they stepped up on a
good day. Lasting changes go through a new profile version instead.

## Files

| File | Purpose |
|---|---|
| [`README.md`](./README.md) | This file |
| [`AugmentationProfile.tla`](./AugmentationProfile.tla) | TLA+ specification of AUG-1..AUG-6 |
| [`AugmentationProfile.cfg`](./AugmentationProfile.cfg) | Safety invariants (4,048,527 distinct states, no errors) |
| [`AugmentationProfile-Liveness.cfg`](./AugmentationProfile-Liveness.cfg) | AUG-6 nudge liveness (`NudgeDue`) on a smaller model |

Python implementation lives under [`src/pace/extensions/augmentation_profile/`](../../src/pace/extensions/augmentation_profile/),
tests under [`tests/extensions/test_augmentation_profile.py`](../../tests/extensions/test_augmentation_profile.py).

## Model checking

```bash
cd extensions/augmentation_profile
java -cp tla2tools.jar tlc2.TLC -workers auto -config AugmentationProfile.cfg AugmentationProfile
java -cp tla2tools.jar tlc2.TLC -workers auto -config AugmentationProfile-Liveness.cfg AugmentationProfile
```

Action records snapshot the state each invariant needs when the action
is recorded, so every action is judged by the rules in force at that
moment. The audit log is modeled as a set, since every invariant
quantifies over all recorded actions. User-direct actions are always
permitted and are not modeled; the Python type enforces their AUG-2
shape.

## Usage

```python
from datetime import datetime, timezone

from pace.extensions.augmentation_profile import (
    AugmentationProfile,
    AugmentationAxis,
    AugmentationAction,
    EmergencyTrigger,
    Mediation,
    AxisKind,
    check_skill_maintenance,
    check_emergency_boundary,
)

now = datetime.now(timezone.utc)

profile = AugmentationProfile(
    principal_id="user-123",
    version="v1",
    pcp_version="2026-04-25.v1",
    axes=[
        AugmentationAxis(name="social_interpretation", kind=AxisKind.COMPENSATE),
        AugmentationAxis(name="executive_function",    kind=AxisKind.COMPENSATE),
        AugmentationAxis(name="independent_email",     kind=AxisKind.PRESERVE),
    ],
    emergency_triggers=[
        EmergencyTrigger(name="medical_keyword_detected",
                         description="LLM detected a medical-emergency phrase"),
    ],
    identity_consent=False,
    declared_at=now,
    declared_by="principal",
)

action = AugmentationAction(
    principal_id="user-123",
    axis_name="social_interpretation",
    mediation=Mediation.AGENT_COMPENSATED,
    profile_version="v1",
    task_id="task-42",
    description="decoded sarcasm in incoming message",
    at=now,
)

check_skill_maintenance(profile, action)  # passes
```

## Status

- **Stage:** reference implementation, draft
- **Extension URI:** `https://ravikiran438.github.io/sauvidya-pace/extensions/augmentation-profile/v1`
- **Depends on:** PACE Core 0.1+
- **Changes:** see the repository [CHANGELOG](../../CHANGELOG.md)

## Relationship to PACE Core

This extension is additive. Agents that do not declare an
`AugmentationProfile` continue to operate under PACE Core's
defensive-accommodation model. Agents that do declare one gain
explicit augmentation contracts with six contractual safety
guarantees, without changing any PACE Core invariants (PCP-1, PCP-2,
PCP-3, IM-1, IM-2, CCC-1, CCC-2, AIC-1, AIC-2, AIC-3, AIC-4 are
unchanged).

- `AugmentationProfile` references the principal's
  `PrincipalCapabilityProfile` through `pcp_version`. A profile change
  that implies a new capacity statement MUST also update `pcp_version`.
- The `AdaptiveInteractionContract` governs interaction-time rules;
  this extension operates at the action level, one layer above.

## Open work

- Population-specific augmentation taxonomies (elder care, BCI users,
  autistic users), which are application-layer concerns
- Composition with Phala welfare detectors: which detectors apply at
  which capacity profile
- An empirical study of skill-atrophy rates with and without AUG-4
- Reference profiles for common deployments

## Not in scope

- Specific augmentation algorithms (BCI signal interpretation, social
  cue decoders, executive-function scaffolds), which are agent-local
- Hardware-side augmentation (BCI device calibration, sensor fusion)
- Therapeutic recommendations, which are clinical, not protocol

## Feedback

Open an issue or pull request on this repository and put
`[augmentation-profile]` at the start of the title.

## References

[1] Dahmani, L. & Bohbot, V.D. (2020). Habitual use of GPS negatively
impacts spatial memory during self-guided navigation.
*Scientific Reports*, 10, 6310.
DOI: [10.1038/s41598-020-62877-0](https://doi.org/10.1038/s41598-020-62877-0)

## License

Apache 2.0. See [../../LICENSE](../../LICENSE).
