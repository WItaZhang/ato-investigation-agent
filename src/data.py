"""Load and validate local synthetic investigation inputs."""

import json
from datetime import date
from pathlib import Path


def load_dataset(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    seen = set()
    for row in data["events"]:
        if row["event_id"] in seen:
            raise ValueError("Duplicate event ID")
        seen.add(row["event_id"])
        date.fromisoformat(row["date"])
        if type(row["new_environment"]) is not bool:
            raise ValueError("new_environment must be boolean")
        if row["account_id"] not in data["accounts"]:
            raise ValueError("Event references unknown account")
        if row["client"] not in {"web", "mobile"}:
            raise ValueError("Unknown client")
    return data
