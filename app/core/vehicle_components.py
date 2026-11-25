"""Owned vehicle-component inventory and recommendations."""
from __future__ import annotations

import json
from pathlib import Path

from .paths import DATA_DIR, PROJECT_ROOT, read_json

CATALOG_FILE = DATA_DIR / "vehicle_components.json"
COMPONENT_GUIDE_FILE = DATA_DIR / "components.json"
SNAPSHOT_DIR = PROJECT_ROOT / "snapshots"


def load_catalog() -> dict:
    return read_json(CATALOG_FILE, {}) or {}


def load_guide() -> dict:
    return read_json(COMPONENT_GUIDE_FILE, {}) or {}


def latest_index_path() -> Path | None:
    candidates = sorted(SNAPSHOT_DIR.glob("index_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _roll_parts(value: str, names: dict[str, str], skill_names: dict[str, str] | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if ":" not in text:
        return text
    code, number = text.split(":", 1)
    if code == "skill":
        return f"技能 {((skill_names or {}).get(number) or number)}"
    return f"{names.get(code, code)} {number}"


def build_inventory(index_path: Path | None = None) -> list[dict]:
    path = index_path or latest_index_path()
    if path is None:
        return []
    payload = read_json(path, {}) or {}
    rows = payload.get("vehicle_component_with_user_info")
    if isinstance(rows, dict):
        rows = list(rows.values())
    if not isinstance(rows, list):
        return []
    catalog = load_catalog()
    components = catalog.get("components") or {}
    roll_names = catalog.get("roll_names") or {}
    skill_names = catalog.get("skill_names") or {}
    guide = load_guide()
    recommended = {
        str(item.get("name") or ""): list(item.get("schemes") or [])
        for item in guide.get("components") or []
    }
    requirements = guide.get("requirements") or {}
    grouped: dict[tuple, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        component_id = str(row.get("component_id") or "")
        meta = components.get(component_id) or {}
        name = str(meta.get("name") or component_id)
        type_id = int(meta.get("type") or 0)
        type_name = str(meta.get("type_name") or ("通用" if type_id == 0 else "其他"))
        rolls = tuple(str(row.get(f"roll_{i}") or "") for i in range(1, 6))
        key = (component_id, rolls)
        entry = grouped.get(key)
        if entry is None:
            words = " / ".join(
                part for part in (_roll_parts(value, roll_names, skill_names) for value in rolls) if part
            )
            entry = {
                "id": f"{component_id}:{abs(hash(rolls))}",
                "name": name,
                "type_id": type_id,
                "type_name": type_name,
                "words": words or "无词条",
                "schemes": recommended.get(name, []),
                "count": 0,
                "level": 0,
            }
            grouped[key] = entry
        entry["count"] += 1
    for entry in grouped.values():
        scheme_rules = requirements
        matches = []
        for scheme in recommended.get(str(entry.get("name") or ""), []):
            scheme_reqs = scheme_rules.get(scheme)
            if scheme_reqs is None:
                matches.append(scheme)
                continue
            rules = scheme_reqs.get(str(entry.get("name") or ""))
            if rules is None:
                continue
            words = str(entry.get("words") or "")
            if isinstance(rules, dict):
                main_words = rules.get("main") or []
                required = rules.get("required") or []
                any_words = rules.get("any") or []
                if main_words and not any(word in words for word in main_words):
                    continue
                if required and not all(word in words for word in required):
                    continue
                if any_words and not any(word in words for word in any_words):
                    continue
                matches.append(scheme)
            elif all(str(rule) in words for rule in rules):
                matches.append(scheme)
        entry["schemes"] = matches
    return list(grouped.values())
