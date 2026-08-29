"""Config loading."""
from __future__ import annotations

import os

import yaml


def load_config(path: str = "config.yaml") -> dict:
    if not os.path.exists(path):
        # Fall back to the shipped example so `localapply` runs out of the box.
        path = "config.example.yaml"
    with open(path) as f:
        return yaml.safe_load(f) or {}
