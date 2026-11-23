"""Local favourite units used for screenshots and quick filtering."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .paths import PROJECT_ROOT, read_json, write_json

FAVORITES_FILE = PROJECT_ROOT / "favorites.json"
KINDS = ("doll", "fairy", "sangvis")


class Favorites:
    def __init__(self, path: Path = FAVORITES_FILE):
        self.path = path
        self._data: dict[str, set[str]] = {kind: set() for kind in KINDS}
        payload = read_json(path, {}) or {}
        rows = payload.get("favorites", payload) if isinstance(payload, dict) else {}
        if isinstance(rows, dict):
            for kind in KINDS:
                values = rows.get(kind) or rows.get(f"{kind}s") or []
                if isinstance(values, list):
                    self._data[kind] = {str(value) for value in values if value}

    def is_favorite(self, kind: str, code: str) -> bool:
        return str(code) in self._data.setdefault(kind, set())

    def set_favorite(self, kind: str, code: str, value: bool) -> None:
        bucket = self._data.setdefault(kind, set())
        if value:
            bucket.add(str(code))
        else:
            bucket.discard(str(code))
        self.save()

    def toggle(self, kind: str, code: str) -> bool:
        value = not self.is_favorite(kind, code)
        self.set_favorite(kind, code, value)
        return value

    def codes(self, kind: str) -> set[str]:
        return set(self._data.get(kind, set()))

    def count(self) -> int:
        return sum(len(values) for values in self._data.values())

    def export_payload(self) -> dict:
        return {
            "version": 1,
            "exported_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "favorites": {kind: sorted(self._data.get(kind, set())) for kind in KINDS},
        }

    def save(self) -> None:
        write_json(self.path, {"favorites": {kind: sorted(values) for kind, values in self._data.items()}})


_favorites: Favorites | None = None


def get_favorites() -> Favorites:
    global _favorites
    if _favorites is None:
        _favorites = Favorites()
    return _favorites
