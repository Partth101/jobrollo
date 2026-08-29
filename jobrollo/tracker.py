"""Simple JSON application tracker. One row per job, appended as you go."""
from __future__ import annotations

import json
import os


class Tracker:
    def __init__(self, path: str = "tracker.json"):
        self.path = path
        self.rows: list[dict] = []
        if os.path.exists(path):
            try:
                self.rows = json.load(open(path))
            except Exception:
                self.rows = []

    def record(self, job: dict, status: str, **extra) -> None:
        row = {
            "company": job.get("company", ""),
            "title": job.get("title", ""),
            "url": job.get("url", ""),
            "ats": job.get("ats", ""),
            "status": status,
            **extra,
        }
        self.rows.append(row)
        json.dump(self.rows, open(self.path, "w"), indent=2)
