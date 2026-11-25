"""Qiushui (秋水) per-activity vehicle-component tables and matching.

Each activity in 秋水Ameth's ranking spreadsheet has one or more
「主战坦克 / 战术人型机甲」 tabs.  Every tab carries a 9-row component table
(4 universal chips + 5 other components).  A component satisfies a row when it
has the same name and carries both 属性词条1 and 属性词条2; 任意词条 is a
recommendation, not a hard requirement.
"""
from __future__ import annotations

from functools import lru_cache

from .paths import DATA_DIR, read_json

CATALOG_FILE = DATA_DIR / "qiushui_components.json"


@lru_cache(maxsize=2)
def load_catalog() -> dict:
    return read_json(CATALOG_FILE, {}) or {}


def activities() -> list[dict]:
    return list(load_catalog().get("activities") or [])


@lru_cache(maxsize=2)
def tables(include_reference: bool = False) -> list[dict]:
    rows: list[dict] = []
    for activity in activities():
        for index, table in enumerate(activity.get("tables") or [], start=1):
            rows.append(
                {
                    "id": str(table.get("id") or f"{activity.get('id')}-{index}"),
                    "activity_id": str(activity.get("id") or ""),
                    "activity": str(activity.get("name") or ""),
                    "side": str(table.get("side") or ""),
                    "variant": str(table.get("variant") or ""),
                    "components": list(table.get("components") or []),
                    "reference": False,
                }
            )
    if include_reference:
        reference = load_catalog().get("reference") or {}
        if reference.get("components"):
            rows.append(
                {
                    "id": "reference",
                    "activity_id": "reference",
                    "activity": "图1 总表（旧版）",
                    "side": "主战坦克",
                    "variant": "参考",
                    "components": list(reference["components"]),
                    "reference": True,
                }
            )
    return rows


@lru_cache(maxsize=8)
def table_entries(activity_id: str | None = None, side: str | None = None, include_reference: bool = False) -> list[dict]:
    """Flatten tables into one row per component requirement."""
    rows: list[dict] = []
    for table in tables(include_reference=include_reference):
        if activity_id and table["activity_id"] != activity_id:
            continue
        if side and table["side"] != side:
            continue
        for index, component in enumerate(table["components"], start=1):
            rows.append(
                {
                    "id": f"{table['id']}:{index}",
                    "table_id": table["id"],
                    "activity_id": table["activity_id"],
                    "activity": table["activity"],
                    "side": table["side"],
                    "variant": table["variant"],
                    "name": str(component.get("name") or ""),
                    "stat1": str(component.get("stat1") or ""),
                    "stat2": str(component.get("stat2") or ""),
                    "optional": str(component.get("optional") or ""),
                    "reference": table["reference"],
                }
            )
    return rows


@lru_cache(maxsize=2)
def requirements_by_name(include_reference: bool = True) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for entry in table_entries(include_reference=include_reference):
        grouped.setdefault(entry["name"], []).append(entry)
    return grouped


def combo_matches(words: str, entry: dict) -> bool:
    text = str(words or "")
    return bool(entry["stat1"] and entry["stat1"] in text and entry["stat2"] and entry["stat2"] in text)


def match_component(name: str, words: str) -> list[dict]:
    if not name:
        return []
    return [
        entry
        for entry in requirements_by_name().get(str(name), [])
        if combo_matches(words, entry)
    ]


def match_inventory(inventory: list[dict], include_reference: bool = True) -> dict[str, dict]:
    """Return ``{row_id: {"count": n, "sources": [words, ...]}}``."""
    by_name: dict[str, list[dict]] = {}
    for item in inventory:
        by_name.setdefault(str(item.get("name") or ""), []).append(item)
    result: dict[str, dict] = {}
    for entry in table_entries(include_reference=include_reference):
        matched = []
        total = 0
        for item in by_name.get(entry["name"], []):
            if combo_matches(str(item.get("words") or ""), entry):
                matched.append(str(item.get("words") or ""))
                total += int(item.get("count") or 0)
        if matched:
            result[entry["id"]] = {"count": total, "sources": matched}
    return result


def union_names(include_reference: bool = True) -> list[str]:
    names: list[str] = []
    for entry in table_entries(include_reference=include_reference):
        if entry["name"] not in names:
            names.append(entry["name"])
    return names


def summary(include_reference: bool = False) -> dict:
    payload = load_catalog()
    table_list = tables(include_reference=include_reference)
    rows = [component for table in table_list for component in table["components"]]
    return {
        "title": str(payload.get("title") or ""),
        "source": str(payload.get("source") or ""),
        "activities": len({table["activity_id"] for table in table_list}),
        "tables": len(table_list),
        "rows": len(rows),
        "components": len({str(component.get("name") or "") for component in rows}),
        "sides": sorted({table["side"] for table in table_list}),
    }
