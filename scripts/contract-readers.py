"""Count contract fields that nothing reads (the CP2 gate).

Every field an orchestrator or guardian sets on the contract should have a
reader: a validator, binding or MCP tool that acts on it. A field with no
reader is a promise nobody keeps. This script lists the contract fields
(InteractionRules, ViolationPolicy, and the fallback fields on
InteractionModality) and searches the reader modules for each name.

    uv run python scripts/contract-readers.py

It also checks the other direction: every contract field the paper names
(Section 3.4) must exist in the code. A field the paper promises and the
code never defined has no reader either, and a reader search cannot see it.

Prints every field with its readers and exits 1 if any field is unread or
missing. A textual search: it can over-count readers, never under-count.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from pace.types import InteractionModality, InteractionRules, ViolationPolicy

ROOT = Path(__file__).resolve().parents[1]
READERS = [
    *sorted((ROOT / "src/pace/validators").glob("*.py")),
    *sorted((ROOT / "src/pace/extensions").rglob("*.py")),
    *sorted((ROOT / "src/pace/ag_ui").glob("*.py")),
    ROOT / "src/pace/mcp_server/tools.py",
]
FIELDS = [
    *(f"interaction_rules.{n}" for n in InteractionRules.model_fields),
    *(f"violation_policy.{n}" for n in ViolationPolicy.model_fields),
    "modality.fallback_chain",
    "modality.escalation_target",
]
assert "fallback_chain" in InteractionModality.model_fields

# Contract fields named in the paper, Section 3.4 (interaction_rules and
# violation_policy). Keep in step with the paper.
PAPER_FIELDS = {
    "interaction_rules": [
        "response_timeout_seconds", "max_options_per_turn", "confirmation_style",
        "language", "speech_rate", "information_density", "memory_aid",
        "guardian_cc", "valid_time_windows", "sundown_block",
        "max_interactions_per_day", "escalation_on_confusion",
        "non_response_policy",
    ],
    "non_response_policy": ["max_retries", "retry_delay", "escalate_after"],
    "violation_policy": [
        "on_time_window_violation", "on_option_overload",
        "on_language_mismatch", "on_capacity_check_skip",
    ],
}


def main() -> int:
    sources = {p: p.read_text(encoding="utf-8") for p in READERS}
    unread = []
    for field in FIELDS:
        name = field.split(".", 1)[1]
        hits = [
            str(p.relative_to(ROOT))
            for p, text in sources.items()
            if re.search(rf"\b{re.escape(name)}\b", text)
        ]
        print(f"{len(hits):>2}  {field}" + (f"  ({', '.join(hits)})" if hits else ""))
        if not hits:
            unread.append(field)
    print(f"\n{len(unread)} of {len(FIELDS)} contract fields have no reader")

    nested = InteractionRules.model_fields.get("non_response_policy")
    code = {
        "interaction_rules": InteractionRules.model_fields,
        "non_response_policy": nested.annotation.model_fields if nested else {},
        "violation_policy": ViolationPolicy.model_fields,
    }
    missing = [
        f"{group}.{name}"
        for group, names in PAPER_FIELDS.items()
        for name in names
        if name not in code[group]
    ]
    for field in missing:
        print(f"MISSING  {field}  (named in the paper, not defined in the code)")
    print(f"{len(missing)} paper contract fields missing from the code")
    return 1 if unread or missing else 0


if __name__ == "__main__":
    sys.exit(main())
