"""Config loading.

Everything lives in one private file: `secret.yaml` (copy it from
`secret.example.yaml`). It holds the model, your profile + background, your
canonical answers, search terms, and behavior. It is git-ignored.
"""
from __future__ import annotations

import os

import yaml

_CANDIDATES = ("secret.yaml", "secret.yml", "secret.example.yaml")


def load_config(path: str | None = None) -> dict:
    for p in ([path] if path else []) + list(_CANDIDATES):
        if p and os.path.exists(p):
            with open(p) as f:
                return yaml.safe_load(f) or {}
    raise FileNotFoundError(
        "No secret.yaml found. Copy secret.example.yaml to secret.yaml and fill it in."
    )
