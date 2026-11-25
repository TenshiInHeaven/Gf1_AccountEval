"""Owned vehicle-component inventory and recommendations."""
from __future__ import annotations

from pathlib import Path

from . import qiushui_catalog, scheme_catalog
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


def index_path_for_account(state) -> Path | None:
    """Map an account snapshot to a compatible component ``index_*`` file.

    Imported ``account_*.json`` files often have no sibling index; fall back to
    the newest index only when its ``user_info.user_id`` matches the loaded
    account (otherwise a different user's components would leak in).
    """
    source = getattr(state, "source_path", None) if state is not None else None
    account = getattr(state, "account", None) if state is not None else None
    account_uid = str(getattr(account, "uid", "") or "")

    def compatible(path: Path) -> bool:
        try:
            payload = read_json(path, {}) or {}
        except Exception:
            return True
        index_uid = str((payload.get("user_info") or {}).get("user_id") or "")
        return not (account_uid and index_uid and account_uid != index_uid)

    if source is not None:
        candidate = SNAPSHOT_DIR / Path(source).name.replace("account_android_", "index_").replace("account_", "index_")
        if candidate.is_file() and compatible(candidate):
            return candidate
    latest = latest_index_path()
    if latest is None:
        return None
    return latest if compatible(latest) else None


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


def _match_rule(words: str, rules) -> bool:
    if isinstance(rules, dict):
        main_words = rules.get("main") or []
        required = rules.get("required") or []
        any_words = rules.get("any") or []
        if main_words and not any(str(word) in words for word in main_words):
            return False
        if required and not all(str(word) in words for word in required):
            return False
        if any_words and not any(str(word) in words for word in any_words):
            return False
        return True
    return all(str(rule) in words for rule in rules or [])


def rule_matches(words: str, rules) -> bool:
    """Public wrapper for the 老吴 accepted-affix rules."""
    return _match_rule(words, rules)


def _guihai_by_weapon() -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for entry in scheme_catalog.catalog_entries():
        grouped.setdefault(entry["weapon"], []).append(entry)
    return grouped


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
    guihai_by_weapon = _guihai_by_weapon()
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
                "guihai_matches": [],
                "qiushui_matches": [],
            }
            grouped[key] = entry
        entry["count"] += 1
    for entry in grouped.values():
        name = str(entry.get("name") or "")
        words = str(entry.get("words") or "")
        matches: list[str] = []
        guihai_matches: list[str] = []
        qiushui_matches: list[str] = []
        for scheme in recommended.get(name, []):
            if scheme == "guihai":
                hit = [
                    combo
                    for combo in guihai_by_weapon.get(name, [])
                    if scheme_catalog.combo_matches(words, combo["words"])
                ]
                if hit:
                    matches.append(scheme)
                    guihai_matches = [combo["label"] for combo in hit]
                continue
            if scheme == "qiushui":
                hit = qiushui_catalog.match_component(name, words)
                if hit:
                    matches.append(scheme)
                    qiushui_matches = [
                        f"{item['activity']} / {item['side']}（{item['variant']}）："
                        f"{item['stat1']} + {item['stat2']}"
                        for item in hit
                    ]
                continue
            scheme_reqs = requirements.get(scheme) or {}
            rules = scheme_reqs.get(name)
            if rules is None:
                matches.append(scheme)
                continue
            if _match_rule(words, rules):
                matches.append(scheme)
        entry["schemes"] = matches
        entry["guihai_matches"] = guihai_matches
        entry["qiushui_matches"] = qiushui_matches
    return list(grouped.values())
