# Consumers

One five-minute story per persona, written before the feature it needs.
Each story is the acceptance test for the checkpoint that builds it.
Status is honest: ✅ runs on the real surface, ✅ (fixture) runs on
synthetic data, ❌ not built.

## Principal: Lakshmi, 78, Hyderabad

Telugu 1.0, English 0.3, low vision, fluctuating decision capacity.
Sundown block 17:00–08:00 IST.

- **10:15 IST** A home-aide booking agent needs a choice. It speaks only
  English; the orchestrator routes the call to a Telugu-speaking sub-agent.
- **10:16** Her phone rings. A slow voice in Telugu: "Amma, two home aide
  services. The first comes Monday and Thursday. The second comes every
  day. Which would you like, or shall I ask Ravi?"
- **10:18** She says "the first one". The agent repeats it back. Consent is
  recorded with a capacity check of her.
- **18:40** Another agent, hosted in Texas where it is 08:10 in the
  morning, wants to confirm the booking. Nothing happens: her contract's
  windows are in her time zone, so it waits for 09:00 IST.
- **She never** hears English, gets more than two choices, gets a call
  during sundown, or has her "yes" stand in for a decision she didn't follow.

Surfaces: Telugu voice through a sub-agent, the AIC, the capacity check,
the consent annotation.
**The one number:** interactions that reach her outside her windows, in a
language she can't follow, or with more than two options: **0**.
Status: ❌ not built end to end. The validators reject each case on its own
(✅ fixture); no agent network runs the story. This is the demo.

## Guardian: Ravi, Texas

- **08:10 CDT** (18:40 IST) A notification: "An agent tried to call Amma
  during her sundown block. It was blocked and will retry at 09:00 IST."
  It names the agent, the rule, the action taken, and what he can do.
- **08:12** He opens her contract, sees the sundown block, and leaves it.
- **08:14** He blocks that agent for repeat attempts, or does nothing.
- **He never** reads raw logs, converts time zones in his head, or learns
  her capacity scores (CCC-2).

Surfaces: a guardian notification payload, a readable view of the
contract, the violation notice.
**The one number:** violations that reach him with enough to act on
(agent, rule, local times in both zones, action taken): **100%**.
Status: ❌. `notify_guardian` is a string with no payload, and time
windows have no time zone (perturbations 16 and 18).

## Agent developer

- **14:00** Clones the repo after reading the article.
- **14:02** `uv sync`, runs the quick start, sees the IM-2 rejection with
  the next step spelled out.
- **14:04** Adds the PACE entry to their AgentCard and runs
  `a2a-testbed validate` against the published manifest. It passes.
- **14:05** Wires `pace-mcp` into their MCP client to check modalities
  while developing.
- **They never** read the paper to get started.

Surfaces: README quick start, `v1/manifest.json`, `pace-mcp`, a2a-testbed.
**The one number:** minutes from clone to a validated AgentCard: **≤ 5**.
Status: ✅ (fixture). The quick start output is checked against the README
and the card validated in a2a-testbed, but the AgentCard was hand-written
and the clock was not measured.

## Accessibility reviewer

- **19:30** Reads the article, clicks "feedback form".
- **19:31** Picks "Thinking, memory or attention" from a plain-language list.
- **19:35** Describes an agent reading three options too fast, and what
  would work instead. Submits.
- **They never** need to know what a PCP or an AIC is.

Surfaces: the capability-feedback issue form, CONTRIBUTING.
**The one number:** share of submissions completed without protocol terms
or follow-up questions. Not yet measurable.
Status: pending. The form exists; there are no submissions yet.
