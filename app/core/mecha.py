"""Mecha component guidance from the tank / tactical mech sheets."""
from __future__ import annotations

from functools import lru_cache

from .paths import DATA_DIR, read_json


@lru_cache(maxsize=1)
def get_mecha_data() -> dict:
    payload = read_json(DATA_DIR / "mecha_components.json", {}) or {}
    return payload


def classification(component: dict, scheme_count: int) -> str:
    schemes = component.get("schemes") or []
    if scheme_count and len(schemes) >= scheme_count:
        return "must"
    if schemes:
        return "partial"
    return "fw"
