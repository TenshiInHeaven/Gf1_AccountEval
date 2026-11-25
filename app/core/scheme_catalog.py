"""Guihai (归海) vehicle-weapon catalog and matching helpers.

The catalog is the machine-readable form of ``机动装甲武器.png``: every
recommended 主词条 / 副词条1 / 副词条2 row is one combo.  A component matches a
combo only when its own words contain every word of that combo.
"""
from __future__ import annotations

from functools import lru_cache

from .paths import DATA_DIR, read_json

CATALOG_FILE = DATA_DIR / "guihai_weapons.json"


@lru_cache(maxsize=2)
def load_catalog() -> dict:
    return read_json(CATALOG_FILE, {}) or {}


@lru_cache(maxsize=2)
def catalog_entries() -> list[dict]:
    """Flatten the nested catalog into one row per recommended combo."""
    rows: list[dict] = []
    payload = load_catalog()
    for group in payload.get("groups") or []:
        for weapon in group.get("weapons") or []:
            if weapon.get("mains"):
                for main in weapon["mains"]:
                    for combo in main.get("combos") or []:
                        words = [str(main.get("word") or "")] + [str(word) for word in combo]
                        rows.append(
                            {
                                "id": f"gh-{len(rows) + 1:03d}",
                                "group": str(group.get("name") or ""),
                                "weapon": str(weapon.get("name") or ""),
                                "main": str(main.get("word") or ""),
                                "words": words,
                                "label": " + ".join(words),
                            }
                        )
            else:
                for combo in weapon.get("combos") or []:
                    words = [str(word) for word in combo]
                    rows.append(
                        {
                            "id": f"gh-{len(rows) + 1:03d}",
                            "group": str(group.get("name") or ""),
                            "weapon": str(weapon.get("name") or ""),
                            "main": "",
                            "words": words,
                            "label": " + ".join(words),
                        }
                    )
    return rows


def catalog_summary() -> dict:
    payload = load_catalog()
    entries = catalog_entries()
    weapons = {
        str(weapon.get("name") or "")
        for group in payload.get("groups") or []
        for weapon in group.get("weapons") or []
    }
    main_rows = sum(
        1
        for group in payload.get("groups") or []
        for weapon in group.get("weapons") or []
        for _ in weapon.get("mains") or []
    )
    main_words = {entry["main"] for entry in entries if entry["main"]}
    chips = sum(
        1
        for group in payload.get("groups") or []
        for weapon in group.get("weapons") or []
        if not weapon.get("mains")
    )
    return {
        "title": str(payload.get("title") or ""),
        "source": str(payload.get("source") or ""),
        "weapons": len(weapons),
        "mains": len(main_words),
        "main_rows": main_rows,
        "chips": chips,
        "entries": len(entries),
        "groups": [str(group.get("name") or "") for group in payload.get("groups") or []],
    }


def combo_matches(words: str, combo_words: list[str]) -> bool:
    text = str(words or "")
    return all(str(word) in text for word in combo_words)


def match_inventory(inventory: list[dict], entries: list[dict] | None = None) -> dict[str, dict]:
    """Return ``{catalog_id: {"count": n, "sources": [owned word strings]}}``."""
    rows = entries if entries is not None else catalog_entries()
    by_name: dict[str, list[dict]] = {}
    for item in inventory:
        by_name.setdefault(str(item.get("name") or ""), []).append(item)
    result: dict[str, dict] = {}
    for entry in rows:
        matched = []
        total = 0
        for item in by_name.get(entry["weapon"], []):
            if combo_matches(str(item.get("words") or ""), entry["words"]):
                matched.append(str(item.get("words") or ""))
                total += int(item.get("count") or 0)
        if matched:
            result[entry["id"]] = {"count": total, "sources": matched}
    return result
