"""Export/import of the complete tier-list and recommendation bundle."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .paths import TIER_DIR, read_json, write_json
from .tiers import RECOMMEND_LEVELS, normalize_recommend

LOCAL_FILES = {
    "doll": "dolls.local.json",
    "fairy": "fairies.local.json",
    "sangvis": "sangvis.local.json",
}
KINDS = ("doll", "fairy", "sangvis")


def _payload_from_tierlist(kind: str, tierlist) -> dict:
    entries = []
    for entry in tierlist.entries:
        row = dict(entry)
        if "recommend" not in row:
            row["recommend"] = tierlist.recommend_level(
                code=str(row.get("code") or ""),
                name=str(row.get("name") or ""),
            )
        entries.append(row)
    return {
        "version": tierlist.version,
        "title": tierlist.title,
        "source": tierlist.source,
        "note": tierlist.note,
        "default_tier": tierlist.default_tier,
        "tiers": [
            {
                "id": tier.id,
                "label": tier.label,
                "name": tier.name,
                "color": tier.color,
                "score": tier.score,
            }
            for tier in tierlist.tiers
        ],
        "entries": entries,
    }


def export_bundle() -> dict:
    from .tiers import get_tierlists

    return {
        "schema": 1,
        "exported_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "kinds": {
            kind: _payload_from_tierlist(kind, tierlist)
            for kind, tierlist in get_tierlists().items()
        },
    }


def validate_bundle(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("评分 JSON 必须是对象")
    kinds = payload.get("kinds")
    if not isinstance(kinds, dict):
        raise ValueError("评分 JSON 缺少 kinds")
    for kind in KINDS:
        data = kinds.get(kind)
        if not isinstance(data, dict):
            raise ValueError(f"评分 JSON 缺少 {kind}")
        tiers = data.get("tiers")
        entries = data.get("entries")
        if not isinstance(tiers, list) or not tiers:
            raise ValueError(f"{kind}.tiers 必须是非空数组")
        if not isinstance(entries, list):
            raise ValueError(f"{kind}.entries 必须是数组")
        ids = set()
        for tier in tiers:
            if not isinstance(tier, dict) or not tier.get("id"):
                raise ValueError(f"{kind}.tiers 中存在缺少 id 的项")
            ids.add(str(tier["id"]))
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("name"):
                raise ValueError(f"{kind}.entries 中存在缺少 name 的项")
            if str(entry.get("tier") or "") not in ids:
                raise ValueError(
                    f"{kind} 的 {entry.get('name')} 使用未知档位 {entry.get('tier')!r}"
                )
            if "recommend" in entry and normalize_recommend(entry.get("recommend")) not in RECOMMEND_LEVELS:
                raise ValueError(
                    f"{kind} 的 {entry.get('name')} recommend 必须是 "
                    "gold/green/blue/white/gray"
                )


def import_bundle(payload: dict) -> None:
    validate_bundle(payload)
    for kind in KINDS:
        write_json(TIER_DIR / LOCAL_FILES[kind], payload["kinds"][kind])


def reset_local_ratings() -> None:
    for filename in LOCAL_FILES.values():
        try:
            (TIER_DIR / filename).unlink()
        except FileNotFoundError:
            pass


def bundle_path_from_file(path: Path) -> dict:
    payload = read_json(path, None)
    if not isinstance(payload, dict):
        raise ValueError(f"无法读取评分 JSON：{path}")
    validate_bundle(payload)
    return payload
