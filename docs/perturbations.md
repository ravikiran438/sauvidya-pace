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
| 17 | An agent's InteractionModality sets a 60 s timeout under a contract that says 300 s | Passed every check: 13 of 20 contract fields had no reader | **bug**, fixed in CP2: AIC-5 `validate_modality_contract` checks the plan against its contract |
| 18 | A violation triggers `notify_guardian` | It was a string; no notification payload existed | **bug**, fixed in CP2: `enforce_violation` returns a `GuardianNotification` with both clocks and the next allowed contact |

Round 1: 11 bug · 4 gap · 2 ok · 1 open (perturbations 16, 17 and 18 were open, fixed in CP2).

## Round 2 — during CP2 (2026-10-10)

| # | Say X happens… | What the system did | Result |
|---|---|---|---|
| 19 | An MCP client reads the `validate_time_window` tool description | It promised a time "in the contract's declared timezone"; the contract had none | **bug**, fixed: the tool takes a timestamp with a UTC offset |
| 20 | An agent in Chicago keeps the same 21:30 schedule across the US daylight-saving change (India has none) | Her local time moves from 08:00 to 09:00; the first is blocked, the second allowed | **ok**: conversion uses the zone database; `test_same_wall_clock_across_us_dst_change` |
| 21 | An agent passes a time with no zone | Rejected: a naive time cannot say whose clock it came from | **ok**: `test_naive_timestamp_rejected` |
| 22 | A guardian enters "Asia/Hyderabad" as her time zone | Rejected at construction: not an IANA zone (Hyderabad uses `Asia/Kolkata`) | **ok**: `test_unknown_timezone_rejected` |
| 23 | An agent ships with `ModalityPlan` defaults (60 s, rate 1.0, 5 options, no recap) | AIC-5 reports all six violations at once, as data (`problems`) | **ok**: `test_default_plan_reports_every_violation` |
| 24 | I count unread contract fields by hand for the CP2 gate | I reported 12 of 18; the grep output I was reading showed 13 | **bug** (in the record), fixed: `scripts/contract-readers.py` measures it |
| 25 | Someone asks whether AIC-1 to AIC-4 are all implemented | AIC-3 (no immediate retry, escalate after repeated non-responses) had no field and no validator: `non_response_policy` from the paper did not exist in the code | **bug**, fixed in C16: `NonResponsePolicy` and `validate_retry` |
| 26 | A validator reads the manifest's AIC-3 invariant | It cited `non_response_policy.escalate_after`, a field the code never defined; written from the paper without checking | **bug**, fixed: the manifest says AIC-3 is not yet implemented until C16 |
| 27 | `contract-readers.py` is asked about a field the paper promises but the code never defined | It only checked fields that exist, so it could not see a missing one | **gap**, fixed in C16: it compares the paper's §3.4 fields with the code; run on the code before C16 it reports the 4 missing AIC-3 fields |
| 28 | A guardian's notification is built with a capacity signal attached | Rejected: `GuardianNotification` forbids unknown fields | **ok**: `test_notification_cannot_carry_capacity_data` |
| 29 | A guardian writes the paper's policy form, `"reject_interaction + notify_guardian"` | Parsed into structured actions; an unknown action is rejected | **ok**: `test_paper_string_form_accepted`, `test_unknown_action_rejected` |
| 30 | A guardian sets `escalate_after: 3` with `max_retries: 1` | The agent would run out of retries after two misses and never escalate: she would be dropped with nobody told | **gap**, fixed: `NonResponsePolicy` requires `escalate_after <= max_retries + 1`; a test walks every valid policy to escalation |
| 31 | She misses the 10:15 call, then answers at 14:00 | The count resets: an answer ends the run of non-responses | **ok**: `test_an_answer_resets_the_count` |
| 32 | Three agents (booking, pharmacy, insurance) each call her once on the same day | `max_interactions_per_day` had no reader, and no counting unit was defined: per agent, each was under its limit | **gap**, fixed in C17: counted per principal across all agents; the fourth call is blocked |
| 33 | An agent checks at 05:00 IST, which is still yesterday in UTC | Counting by her local day: yesterday's calls don't block her first call of the day | **ok**: `test_utc_day_would_count_the_wrong_calls` |
| 34 | A reader trusts the AgentCard's `supported_modalities` description | It said validators cross-check it against the modality; none did | **bug**, fixed in C18: `validate_channels` checks every channel against it |
| 35 | Someone compares the agent's channels with the card's and the paper's | Three vocabularies: `voice/text/visual/haptic`, `large_text/simple_visual`, `text_large_font` | **bug**, fixed: one vocabulary (PrimaryChannel, plus `guardian_relay` for fallbacks); a2a-testbed now rejects `large_text` through the manifest |
| 36 | Her voice channel is down and the plan falls back to a text message, but she cannot read | `fallback_chain` had no reader; the fallback would have been used | **gap**, fixed: every channel, primary and fallback, must reach her; a chain must end in `guardian_relay` or an escalation target |

Round 2: 18 questions — 6 bug · 4 gap · 8 ok · 0 open.

## Round 3 — during CP3 (2026-10-11)

| # | Say X happens… | What the system did | Result |
|---|---|---|---|
| 37 | CP3's claim lists "an agent on another clock" as a case a prompt cannot see | A prompt that names her time zone ties: a perfect listener on Chicago time converts | **bug** (in the claim), fixed: moved to the controls; the claim is narrowed |
| 38 | CP3's claim lists "a sub-agent that never saw the prompt" | A prompt that says "pass this on" reaches the sub-agent and ties | **bug** (in the claim), fixed: moved to the controls |
| 39 | Three agents each ask for her twice a day, against a limit of three | PACE keeps the limit, and the last request waits 65 hours; requests queue first come, first served | **ok**, out of scope: PACE caps her contacts, and choosing which request spends them is outside PACE (see Scope in decisions.md) |
| 40 | Every contact routes through one hub the family keeps current | A prompt to that hub ties PACE on every case, including agents nobody set up | **ok**: a control; PACE's gain is that agents from other vendors can read her contract without such a hub |
| 41 | A guardian relay (in CP3's original claim) | Consent is not a contact, so this experiment cannot score it; a perfect listener told "only her consent counts" would refuse the relayed yes | **open**: CCC-4 needs its own measurement |

Round 3: 5 questions — 2 bug · 0 gap · 2 ok · 1 open.

## Candidates

- The PCP is updated mid-call.
- Daylight saving time shifts the guardian's clock but not hers.
- The guardian is unreachable for three days.
- The guardian changes, or the principal revokes the guardian at a lucid moment.
- Her capability improves and the PCP should step back up.
- Slow responses from a tremor read as cognitive decline (paper §8).
- An agent caches an old AIC version.
- Her device is offline when an agent needs the PCP.
- Two orchestrators hold different PCP versions.
- A reviewer pastes identifiable health details into the public feedback form.
