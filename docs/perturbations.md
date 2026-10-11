# Perturbations

Questions asked of the code, not the design: **"Say X happens — what does
the system do?"** Answered by reading the source and running it.

Legend: **bug** (behavior was wrong, now fixed) · **gap** (undefined or
unobservable, now has a signal) · **ok** (handled, with the reason) ·
**open** (recorded, not changed yet, with the reason).

## Round 1 — during CP1 (2026-10-09 to 2026-10-10)

| # | Say X happens… | What the system did | Result |
|---|---|---|---|
| 1 | An agent calls the paper's example principal (Telugu 1.0, English 0.3, `language:te` required) in English | `validate_language_match` passed: it only checked the language was listed | **bug**, fixed: pin first, then fluency floor |
| 2 | The principal re-declares an axis `preserve` after the agent helped under `compensate` | TLC: `SkillMaintenance` violated in 4 steps; Python audits had the same false positive | **bug**, fixed: per-action snapshot and profile versions |
| 3 | Someone holds an ActiveChallenge record but not the transcript | Hashing "yes", "no" and a few likely answers recovers the response | **bug**, fixed: HMAC under an on-device key, bound to `challenge_id` |
| 4 | The MCP SDK ships a major version (2.x) | `pace-mcp` failed to start on a fresh install | **bug**, fixed: SDK 2.x handlers |
| 5 | An agent declares the augmentation URI from the code constant | It pointed at `github.com/...`, where no manifest is served | **bug**, fixed |
| 6 | A validator reads the augmentation manifest's invariants | They were named AP-1..3; code, TLA+ and tools use AUG-1..5 | **bug**, fixed: generated manifests |
| 7 | A reviewer runs TLC to confirm the README's "6 verified properties" | 5 are TLC invariants; the rest are action guards or not modeled | **bug** (claim), fixed |
| 8 | Someone installs the MCP server from the documented `@v0.1.0` tag | The tag predates the SDK 2.x fix and fails to start | **bug**, fixed for `main`; tag v0.2.0 on release |
| 9 | A manifest-aware validator watches PACE traffic | `wire_artefacts` was empty, so nothing could be checked | **gap**, fixed: three artefacts declared |
| 10 | A step-up's time limit passes while the principal is still writing | Undefined | **gap**, fixed: AUG-6 nudge; help never resumes on its own |
| 11 | No available agent speaks the principal's language | Undefined beyond "escalate" | **gap**, fixed: fallback ladder; IM-2 errors name the next step |
| 12 | A guardian relays the question and answers for her | Nothing distinguished a relayed consent | **gap**, fixed: CCC-4 and `relayed_by` |
| 13 | An emergency while no agent speaks her language | Undefined | **open**: EmergencyRoute is on the roadmap; needs verified jurisdiction numbers |
| 14 | The sundown block crosses midnight (17:00–08:00) | `_in_window` wraps correctly | **ok**: only the 19:00 side was tested; added `test_sundown_block_wraps_past_midnight` (02:00 blocked, 08:01 allowed) |
| 15 | TLC reports a different search depth on two runs (17, 18) | Parallel workers make reported depth approximate; state counts match | **ok**: depth is not published |
| 16 | The agent runs in a US data center; the principal is in Hyderabad | `validate_time_window` took a bare `HH:MM`; neither `TimeWindow` nor the AIC had a time zone. 08:30 CDT is 19:00 IST, inside her sundown block | **bug**, fixed in CP2: required `timezone` on the contract; windows evaluated in her local time |
| 17 | An agent's InteractionModality sets a 60 s timeout under a contract that says 300 s | Passes every check: 12 of 18 contract and modality fields have no reader | **open → CP2**: contract-to-modality test |
| 18 | A violation triggers `notify_guardian` | It is a string; no notification payload exists | **open → CP2**: define the notification |

Round 1: 9 bug · 4 gap · 2 ok · 3 open (perturbation 16 was open, fixed in CP2).

## Round 2 — during CP2 (2026-10-10)

| # | Say X happens… | What the system did | Result |
|---|---|---|---|
| 19 | An MCP client reads the `validate_time_window` tool description | It promised a time "in the contract's declared timezone"; the contract had none | **bug**, fixed: the tool takes a timestamp with a UTC offset |
| 20 | An agent in Chicago keeps the same 21:30 schedule across the US daylight-saving change (India has none) | Her local time moves from 08:00 to 09:00; the first is blocked, the second allowed | **ok**: conversion uses the zone database; `test_same_wall_clock_across_us_dst_change` |
| 21 | An agent passes a time with no zone | Rejected: a naive time cannot say whose clock it came from | **ok**: `test_naive_timestamp_rejected` |
| 22 | A guardian enters "Asia/Hyderabad" as her time zone | Rejected at construction: not an IANA zone (Hyderabad uses `Asia/Kolkata`) | **ok**: `test_unknown_timezone_rejected` |

## Candidates

- Three agents each call her on the same day: is `max_interactions_per_day` per agent or per principal? (counting unit)
- The PCP is updated mid-call.
- Daylight saving time shifts the guardian's clock but not hers.
- The guardian is unreachable for three days.
- The guardian changes, or the principal revokes the guardian at a lucid moment.
- Her capability improves and the PCP should step back up.
- Slow responses from a tremor read as cognitive decline (paper §8).
- An agent caches an old AIC version.
- Her device is offline when an agent needs the PCP.
- Two orchestrators hold different PCP versions.
- Her voice channel is down: is `fallback_chain` followed?
- A reviewer pastes identifiable health details into the public feedback form.
