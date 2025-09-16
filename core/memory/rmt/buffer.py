from __future__ import annotations

from typing import Dict, List, Optional


SLOTS = ("persona", "long_term_facts", "open_loops", "recent_summary")


def compose_prompt(slots: Dict[str, str]) -> str:
    """Compose a compact prompt preamble from RMT slots."""
    lines: List[str] = []
    for name in SLOTS:
        if v := slots.get(name):
            lines.append(f"[{name}]\n{v}")
    return "\n\n".join(lines)

