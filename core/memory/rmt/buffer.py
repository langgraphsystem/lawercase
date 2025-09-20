from __future__ import annotations

SLOTS = ("persona", "long_term_facts", "open_loops", "recent_summary")


def compose_prompt(slots: dict[str, str]) -> str:
    """Compose a compact prompt preamble from RMT slots."""
    lines: list[str] = []
    for name in SLOTS:
        if v := slots.get(name):
            lines.append(f"[{name}]\n{v}")
    return "\n\n".join(lines)
