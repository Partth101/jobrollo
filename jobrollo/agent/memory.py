"""Agent memory.

Two layers:
  * Working memory (this run): the answer decided for each question label, so identical fields
    are answered once and consistently, and progress survives re-observation after each action.
  * Site memory (persisted): per-domain label→answer mappings learned across runs, so the
    agent gets faster and more consistent the more you use it on a given ATS.

Only non-sensitive question→answer mappings are persisted; the résumé and full profile are
never written here.
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlparse


def _norm(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip().lower())[:160]


class Memory:
    def __init__(self, url: str, store_path: str = ".jobrollo_memory.json"):
        self.site = urlparse(url).netloc
        self.store_path = store_path
        self._run: dict[str, str] = {}
        self._site: dict[str, dict[str, str]] = {}
        if os.path.exists(store_path):
            try:
                self._site = json.load(open(store_path))
            except Exception:
                self._site = {}
        self._run.update(self._site.get(self.site, {}))

    def recall(self, label: str) -> str | None:
        return self._run.get(_norm(label))

    def remember(self, label: str, value: str) -> None:
        key = _norm(label)
        self._run[key] = value
        self._site.setdefault(self.site, {})[key] = value

    def acted_refs(self) -> set[str]:
        return getattr(self, "_acted", set())

    def mark_acted(self, ref: str) -> None:
        if not hasattr(self, "_acted"):
            self._acted: set[str] = set()
        self._acted.add(ref)

    def flush(self) -> None:
        try:
            json.dump(self._site, open(self.store_path, "w"), indent=2)
        except Exception:
            pass
