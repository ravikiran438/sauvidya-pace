# PACE — repository status

Snapshot for future-me.

## Last touched

May 1, 2026 — added `AccessibilityServiceRef` AgentCard descriptor +
4 sibling primitives (`PACEConsentAnnotation`, `ActiveChallenge`,
`CCCTrend` + `derive_ccc_trend`, `PACEViolationNotice`), tightened
TLA+ V-3 to require exact AIC version match, added cross-field model
validator on `PACEConsentAnnotation`, wired 5 new MCP validators.

## What works (verified)

- 120 tests passing via shared venv.
- TLA+ model `specification/Pace.tla` checks clean under TLC at the
  current widened model (2 principals, 2 orchestrators, 3 AIC
  versions). New invariants added by this round:
  `ViolationBlockEnforcement` (V-1), `ViolationScopeRespected` (V-3),
  `AnnotationIntegrity`. V-2 is structural (one-hop broadcast
  enforced by the `ApplyViolationNotice` action's lack of mutation
  on `violationNotices`).
- MCP server at `pace.mcp_server` exposes 16 validator tools
  including the 5 new ones (`validate_accessibility_service_ref`,
  `validate_active_challenge`, `validate_pace_consent_annotation`,
  `validate_pace_violation_notice`, `compute_ccc_trend`).
- ExtensionManifest published at `v1/manifest.json` auto-generated
  from `pace.types.AccessibilityServiceRef`.
- Augmentation-profile sub-extension has URI constant + manifest at
  `extensions/augmentation-profile/v1/manifest.json`.

## What's pending

- Repo not yet pushed.
- PACE preprint v3 drafted at `../sauvidya/preprint/sauvidya-accessibility-protocol-v3.md`
  with substantive changes: retires the v2 "pace.* keys inside
  ConsentRecord" pattern in favor of `PACEConsentAnnotation` sibling;
  adds AccessibilityServiceRef, ActiveChallenge, CCCTrend, and
  PACEViolationNotice with V-1/V-2/V-3 rules. Not yet published;
  current Zenodo is v2 (DOI .19633139).
- v3 publication is a **breaking change** for v2-emitted
  `ConsentRecord.pace` blocks. Migration recipe is in §4.1 of the
  v3 preprint draft.

## Re-page-in checklist

1. `cd <here> && ../../.venv/bin/python -m pytest -q` — expect 120/120.
2. Run TLC: `cd specification && java -Xmx4g -cp "$TLA2TOOLS"
   tlc2.TLC -workers auto -deadlock Pace` — expect "no error".
3. Re-read `src/pace/types/accessibility_service_ref.py` and the
   four sibling primitive files for current wire format.
4. `MASTER_STATUS.md` in testbed.

## Files I'd look at first

- `src/pace/types/accessibility_service_ref.py` — AgentCard descriptor.
- `src/pace/types/pace_consent_annotation.py` — sibling to ACAP
  ConsentRecord; the cross-field validator there enforces CCC
  coherence.
- `src/pace/types/active_challenge.py` — tamper-evident active CCC
  evidence (challenge_hash + response_hash + timing + classification).
- `src/pace/types/violation_notice.py` — cross-orchestrator block
  broadcast; `compute_evidence_hash` is the canonical helper.
- `src/pace/types/ccc_trend.py` — `CCCTrend` enum (canonical) +
  `derive_ccc_trend` (reference impl, non-normative).
- `specification/Pace.tla` — V-1, V-3, AnnotationIntegrity verified.

## Known gaps / future work

- V-3 was tightened from "any AIC bound" to "exact version match" in
  this round. TLC re-verifies clean at the widened model. If
  expanded model checking flags issues, treat as new finding.
- ActiveChallenge stores SHA-256 digests of challenge/response text.
  Strong tamper-evidence; weak privacy if anyone has the original
  transcript. Document this in the v3 preprint's privacy section.
- `derive_ccc_trend` ships an OLS-slope reference; deployments are
  free to swap for EWMA/Mann-Kendall/etc as long as outputs map onto
  the canonical four-value enum.
