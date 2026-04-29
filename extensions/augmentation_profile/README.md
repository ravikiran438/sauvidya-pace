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
literature. The five invariants below exist to make these risks
contractual rather than optional.

## What this extension adds

### Primitives

| Primitive | Purpose |
|---|---|
| `AugmentationAxis` | A single dimension of augmentation: `compensate`, `amplify`, or `preserve` |
| `AugmentationProfile` | Per-principal declaration: which axes are augmented, with what reversibility, audit, identity, skill-maintenance, and emergency rules |
| `AugmentationAction` | A logged action with a `mediation` field (`agent_compensated`, `agent_amplified`, `user_direct`, `agent_handed_off`) |
| `EmergencyTrigger` | Declared crisis condition that MUST force human handoff |

### Invariants

| Invariant | Statement |
|---|---|
| **AUG-1 Reversibility** | Every augmentation declared in an `AugmentationProfile` MUST be revertible by the principal. Reversion MUST be a typed event recorded against the profile, not a soft toggle. |
| **AUG-2 Audit Decomposition** | Every `AugmentationAction` MUST carry a `mediation` field distinguishing agent-compensated, agent-amplified, user-direct, and agent-handed-off actions. Aggregate logs that erase this distinction violate AUG-2. |
| **AUG-3 Identity Preservation** | Any agent action that would alter the principal's voice, written style, or expressive identity (impersonation in any direction) MUST cite an `identity_consent` element in the profile. Implicit consent is forbidden. **Note:** AUG-3 is enforced against the agent's self-attestation in `AugmentationAction.alters_identity`. A misbehaving agent that lies about this flag cannot be caught by AUG-3 alone; pair it with detector provenance (Phala WD-4) for end-to-end accountability. |
| **AUG-4 Skill Maintenance** | Capacities marked `preserve` in the profile MUST NOT be replaced by `agent_compensated` or `agent_amplified` actions. The agent MAY scaffold but MUST NOT substitute. |
| **AUG-5 Emergency Boundary** | When any declared `EmergencyTrigger` fires, the agent MUST emit an `agent_handed_off` action and MUST NOT take any further compensating or amplifying action until human acknowledgment. |

## Files

| File | Purpose |
|---|---|
| [`README.md`](./README.md) | This file |
| [`STATUS.md`](./STATUS.md) | Stage, URI, and scope |
| [`AugmentationProfile.tla`](./AugmentationProfile.tla) | TLA+ specification of the five invariants |
| [`AugmentationProfile.cfg`](./AugmentationProfile.cfg) | Small-model TLC configuration |

Python implementation lives under [`src/pace/extensions/augmentation_profile/`](../../src/pace/extensions/augmentation_profile/),
tests under [`tests/extensions/test_augmentation_profile.py`](../../tests/extensions/test_augmentation_profile.py).

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
    description="decoded sarcasm in incoming message",
    at=now,
)

check_skill_maintenance(profile, action)  # passes
```

## Relationship to PACE Core

This extension is additive. Agents that do not declare an
`AugmentationProfile` continue to operate under PACE Core's
defensive-accommodation model. Agents that do declare one gain
explicit augmentation contracts with five contractual safety
guarantees, without changing any PACE Core invariants (PCP-1, PCP-2,
PCP-3, IM-1, IM-2, CCC-1, CCC-2, AIC-1, AIC-2, AIC-3, AIC-4 are
unchanged).

## References

[1] Dahmani, L. & Bohbot, V.D. (2020). Habitual use of GPS negatively
impacts spatial memory during self-guided navigation.
*Scientific Reports*, 10, 6310.
DOI: [10.1038/s41598-020-62877-0](https://doi.org/10.1038/s41598-020-62877-0)

## License

Apache 2.0. See [../../LICENSE](../../LICENSE).
