from __future__ import annotations

import json
from pathlib import Path

STATE_FILE = "data/ingestion_state.json"


def check_queue():
    if not Path(STATE_FILE).exists():
        print("State file not found.")
        return

    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
            queue_size = len(data.get("queue", []))
            visited_size = len(data.get("visited_urls", []))
            print(f"Queue Size: {queue_size}")
            print(f"Visited URLs: {visited_size}")
    except Exception as e:
        print(f"Error reading state file: {e}")


if __name__ == "__main__":
    check_queue()
