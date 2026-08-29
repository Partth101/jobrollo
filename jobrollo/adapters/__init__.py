"""ATS adapter registry. Add a new board by writing a subclass and listing it here."""
from __future__ import annotations

from .ashby import AshbyAdapter
from .base import ATSAdapter, FieldFlag, FillResult
from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter

REGISTRY: list[type[ATSAdapter]] = [GreenhouseAdapter, LeverAdapter, AshbyAdapter]


def get_adapter(url: str) -> ATSAdapter | None:
    for cls in REGISTRY:
        if cls.matches(url):
            return cls()
    return None


__all__ = ["ATSAdapter", "FieldFlag", "FillResult", "get_adapter", "REGISTRY"]
