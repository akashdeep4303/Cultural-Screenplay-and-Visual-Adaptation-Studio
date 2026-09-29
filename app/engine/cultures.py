from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CULTURE_DIR = Path(__file__).resolve().parent.parent / "data" / "cultures"


@lru_cache(maxsize=16)
def load_culture(culture_id: str) -> dict:
    path = CULTURE_DIR / f"{culture_id}.json"
    if not path.exists():
        raise KeyError(f"Unknown culture '{culture_id}'. Available: {available_cultures()}")
    return json.loads(path.read_text(encoding="utf-8"))


def available_cultures() -> list[dict]:
    rows = []
    for path in sorted(CULTURE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "id": data["id"],
                "label": data["label"],
                "dialect": data["dialect"],
                "region": data["region"],
                "scripts": data.get("scripts", ["roman"]),
            }
        )
    return rows
