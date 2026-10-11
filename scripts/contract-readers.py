"""Count contract fields that nothing reads (the CP2 gate).

Every field an orchestrator or guardian sets on the contract should have a
reader: a validator, binding or MCP tool that acts on it. A field with no
reader is a promise nobody keeps. This script lists the contract fields
(InteractionRules, ViolationPolicy, and the fallback fields on
InteractionModality) and searches the reader modules for each name.

    uv run python scripts/contract-readers.py

Prints every field with its readers and exits 1 if any field is unread.
A textual search: it can over-count readers, never under-count them.
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
    return 1 if unread else 0


if __name__ == "__main__":
    sys.exit(main())
