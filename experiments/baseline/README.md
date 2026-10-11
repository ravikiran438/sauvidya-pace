# CP3 baseline: PACE vs. telling each agent

Does PACE stop violations that telling each agent what she needs would
let through? This experiment answers that with **perfect listeners**:
every agent, in both arms, obeys everything it knows.

```bash
uv run python experiments/baseline/run.py          # table
uv run python experiments/baseline/run.py --json   # full result
```

## The two arms

- **prompt.** Each agent the family set up got the best prompt they could
  write: speak Telugu, contact only 09:00–11:00 or 16:00–18:00
  Asia/Kolkata, at most 2 options, at most 3 contacts a day, and pass this
  on to any agent you delegate to. The agent keeps the prompt as it stood
  on the day it was set up, and counts its own contacts. An agent nobody
  set up knows nothing.
- **pace.** Every agent speaks PACE: before each contact it reads her
  current contract from her orchestrator, which also counts contacts
  across agents.

A referee applies the PACE validators to every contact that reached her,
under the contract in force at that moment, in both arms.

## What it can and cannot show

Because the agents are perfect, the PACE arm's zero is by construction.
The experiment does not measure obedience; it measures **what a prompt
cannot carry**. Its value is the split between cases:

- **Controls**, where a good prompt ties: one agent on her clock, an agent
  on another clock (the prompt names her time zone), a sub-agent (the
  prompt is passed on), and every contact routed through one hub the
  family keeps up to date.
- **Structural cases**, where it cannot: an agent nobody set up, three
  agents sharing one daily limit, and a contract changed after the agents
  were told.

It also reports the cost of keeping the rules: deferrals, escalations and
the longest wait. When six asks a day meet a limit of three, the last
request waits days. The PACE arm queues first come, first served; which
request should go first is decided outside PACE.

The overall per-1,000 figure depends on the scenario mix, so read the
per-scenario rows. Commit the script, not the number.

## Running it in a2a-testbed

```bash
uv run python experiments/baseline/run.py --export-testbed out/
a2a-testbed run out/never-told.prompt.yaml        # one scenario, one arm
```

The export writes each scenario and arm as an a2a-testbed scenario
(`a2a-testbed>=0.3.0a1`): every contact that reached her is a step, and
the referee's four rules are extension checks the testbed runs on
pace-mcp, each with the verdict this script expects. `expected.json`
lists the step and violation counts per file. The delegates file pins
pace-mcp to the release the verdicts were computed with; pass
`--mcp-delegates` to use another server. The testbed agrees with the
script when every step passes.

## Next

- A second arm with a real model given the prompt, to measure obedience.
