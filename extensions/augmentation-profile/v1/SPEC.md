# PACE Augmentation-Profile Extension — Wire Specification

> Generated from `v1/manifest.json`. Re-render after the manifest changes; do not hand-edit.

- **Extension URI:** `https://ravikiran438.github.io/sauvidya-pace/extensions/augmentation-profile/v1`
- **Protocol version:** 1.0.0
- **Manifest envelope version:** 1.0.0
- **Publisher:** Ravi Kiran Kadaboina

Active augmentation actions for principals, with reversibility and identity-preservation guarantees.

## AgentCard payload

This extension declares itself by URI presence and does not constrain the AgentCard payload. Validators accept any object in the entry's `params`.

## Invariants

- AP-1: every AugmentationAction MUST be reversible by an AxisRevertedEvent within the declared window.
- AP-2: emergency triggers bypass profile review only for actions explicitly marked emergency-allowed.
- AP-3: principal-skill-maintenance MUST be preserved across augmentation cycles (no skill atrophy).

---

_Drift between this `SPEC.md` and the protocol's pydantic models indicates the manifest needs regenerating. CI may compare a freshly-rendered version against the committed one._
