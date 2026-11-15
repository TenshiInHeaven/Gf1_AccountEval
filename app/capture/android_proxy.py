"""Convert a decrypted GFL ``Index/index`` payload into an account snapshot.

The Android/emulator capture path uses mitmproxy (see
``tools/android_proxy_capture.py``).  This module is deliberately pure stdlib so
the field mapping can be tested without mitmproxy, a device or a game account.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any


class AndroidCaptureError(ValueError):
    pass


def _norm(key: Any) -> str:
    return "".join(ch for ch in str(key).lower() if ch.isalnum())


def _get(mapping: Any, *names: str, default: Any = None) -> Any:
    if not isinstance(mapping, dict):
        return default
    lookup = {_norm(key): value for key, value in mapping.items()}
    for name in names:
        key = _norm(name)
        if key in lookup:
            return lookup[key]
    return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _list_at(payload: dict, keys: tuple[str, ...]) -> list[dict]:
    wanted = {_norm(key) for key in keys}
    for key, value in payload.items():
        if _norm(key) in wanted and isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    # Some responses nest the actual index payload under data/result.
    for key in ("data", "result", "index", "user_data"):
        value = payload.get(key)
        if isinstance(value, dict):
            found = _list_at(value, keys)
            if found:
                return found
    return []


def _find_list_by_shape(payload: dict, markers: tuple[str, ...]) -> list[dict]:
    """Best-effort fallback when the server uses a different key name."""
    wanted = {_norm(marker) for marker in markers}
    for key, value in payload.items():
        if not isinstance(value, list) or not value:
            continue
        first = value[0]
        if not isinstance(first, dict):
            continue
        row_keys = {_norm(item) for item in first}
        if row_keys & wanted:
            return [item for item in value if isinstance(item, dict)]
    for key in ("data", "result", "index", "user_data"):
        value = payload.get(key)
        if isinstance(value, dict):
            found = _find_list_by_shape(value, markers)
            if found:
                return found
    return []


def _codex_maps(root: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for kind in ("dolls", "fairies", "sangvis"):
        by_id: dict[str, str] = {}
        path = root / "app" / "data" / "codex" / f"{kind}.json"
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("code") or "")
            info_id = str(row.get("id") or "")
            if code and info_id:
                by_id[info_id] = code
        result[kind] = by_id
    return result


def _meta(payload: dict) -> dict:
    candidates = []
    for key in ("user_info", "userInfo", "base_info", "baseInfo", "player", "account"):
        value = payload.get(key)
        if isinstance(value, dict):
            candidates.append(value)
    candidates.append(payload)
    source = next((item for item in candidates if _get(item, "uid", "userId", "user_id") is not None), payload)
    level = _get(source, "level", "user_level", "userLevel", default=0)
    meta = {
        "uid": str(_get(source, "uid", "userId", "user_id", default="") or ""),
        "nickname": str(
            _get(source, "nickname", "name", "user_name", "userName", default="") or ""
        ),
        "level": _int(level),
        "max_gun": _int(_get(source, "max_gun", "maxGun", "max_gun_num", default=0)),
        "max_sangvis": _int(
            _get(source, "max_sangvis", "maxSangvisGun", "max_sangvis_gun", default=0)
        ),
        "max_fairy": _int(_get(source, "max_fairy", "maxFairy", default=0)),
        "max_equip": _int(_get(source, "max_equip", "maxEquip", default=0)),
        "source": "Android MITM · Index/index",
        "captured_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "game": "少女前线 Android",
        "note": "从模拟器 HTTPS 代理抓取的 Index/index 响应转换；只读，不修改游戏。",
    }
    return meta


def _dolls(payload: dict, codex: dict[str, str]) -> list[dict]:
    rows = _list_at(
        payload,
        ("gun_with_user_info", "gun_list", "guns", "user_guns", "dolls", "gun_info"),
    ) or _find_list_by_shape(payload, ("gun_id", "gunId", "gun_code", "gunCode"))
    result = []
    for row in rows:
        info_id = _get(row, "gun_id", "gunId", "info_id", "infoId", "id")
        code = str(_get(row, "code", "gun_code", "gunCode", default="") or "")
        if not code:
            code = codex.get(str(info_id), str(info_id or ""))
        result.append(
            {
                "uid": _int(_get(row, "id", "user_id", "userId", "uid")),
                "code": code,
                "level": _int(_get(row, "level")),
                "exp": _int(_get(row, "exp", "experience")),
                "favor": _int(_get(row, "favor", "favorability")),
                "team_id": _int(_get(row, "team_id", "teamId")),
                "skin_id": _int(_get(row, "skin_id", "skinId", "skin")),
                "location": _int(_get(row, "location")),
                "number": _int(_get(row, "number", "count")),
                "mod": _int(_get(row, "mod", "mod_level", "modLevel")),
            }
        )
    return result


def _fairies(payload: dict, codex: dict[str, str]) -> list[dict]:
    rows = _list_at(
        payload,
        ("fairy_with_user_info", "fairy_list", "fairies", "user_fairies"),
    ) or _find_list_by_shape(payload, ("fairy_id", "fairyId", "quality_level", "qualityLevel"))
    result = []
    for row in rows:
        info_id = _get(row, "fairy_id", "fairyId", "info_id", "infoId", "id")
        code = str(_get(row, "code", "fairy_code", "fairyCode", default="") or "")
        if not code:
            code = codex.get(str(info_id), str(info_id or ""))
        result.append(
            {
                "id": _int(_get(row, "id", "user_id", "userId", "uid")),
                "code": code,
                "level": _int(_get(row, "level")),
                "exp": _int(_get(row, "exp", "experience")),
                "quality": _int(_get(row, "quality", "quality_level", "qualityLevel")),
                "quality_level": _int(
                    _get(row, "quality", "quality_level", "qualityLevel")
                ),
                "skill_level": _int(
                    _get(row, "skill_level", "skillLevel", "main_skill_level", "mainSkillLevel")
                ),
                "mod": _int(_get(row, "mod")),
                "mod_exp": _int(_get(row, "mod_exp", "modExp")),
                "team_id": _int(_get(row, "team_id", "teamId")),
                "equip_id": _int(_get(row, "equip_id", "equipId")),
                "is_collect": _int(_get(row, "is_collect", "isCollect")),
            }
        )
    return result


def _equipment(payload: dict) -> list[dict]:
    rows = _list_at(
        payload,
        ("equip_with_user_info", "equip_list", "equipment", "equips", "user_equips"),
    ) or _find_list_by_shape(payload, ("info_id", "infoId", "own_number", "ownNumber"))
    result = []
    for row in rows:
        info = row.get("info") if isinstance(row.get("info"), dict) else {}
        info_id = _get(row, "info_id", "infoId", "equip_id", "equipId")
        if info_id is None:
            info_id = _get(info, "id", "info_id")
        result.append(
            {
                "id": _int(_get(row, "id", "user_id", "userId", "uid")),
                "gun_id": _int(_get(row, "gun_id", "gunId")),
                "info_id": _int(info_id),
                "own_number": _int(
                    _get(row, "own_number", "ownNumber", "number", "count")
                ),
                "equip_level": _int(
                    _get(row, "equip_level", "equipLevel", "level")
                ),
                "equip_exp": _int(_get(row, "equip_exp", "equipExp", "exp")),
            }
        )
    return result


def _sangvis(payload: dict, codex: dict[str, str]) -> list[dict]:
    rows = _list_at(
        payload,
        ("sangvis_with_user_info", "sangvis_list", "sangvis", "coalition", "user_sangvis"),
    ) or _find_list_by_shape(payload, ("info_id", "infoId", "advance", "resolution_level"))
    result = []
    for row in rows:
        info_id = _get(row, "info_id", "infoId", "sangvis_id", "sangvisId", "id")
        code = str(_get(row, "code", "sangvis_code", "sangvisCode", default="") or "")
        if not code:
            code = codex.get(str(info_id), str(info_id or ""))
        result.append(
            {
                "info_id": _int(info_id),
                "code": code,
                "level": _int(_get(row, "level")),
                "advance": _int(_get(row, "advance", "advance_level", "advanceLevel")),
                "resolution_level": _int(
                    _get(row, "resolution_level", "resolutionLevel")
                ),
                "sign": _int(_get(row, "sign")),
                "skin": _int(_get(row, "skin", "skin_id", "skinId")),
                "break_through": _int(
                    _get(row, "break_through", "breakThrough", "break_through_level")
                ),
                "chip1": _get(row, "chip1"),
                "chip2": _get(row, "chip2"),
            }
        )
    return result


def build_snapshot(payload: dict, *, project_root: Path | None = None) -> dict:
    """Convert a decoded ``Index/index`` dict to the app's snapshot schema.

    Raises :class:`AndroidCaptureError` when the payload does not contain any
    recognisable account lists, so a targettrain-only packet is never turned
    into a fake empty account.
    """
    if not isinstance(payload, dict):
        raise AndroidCaptureError("Index 响应不是 JSON 对象")
    root = project_root or Path(__file__).resolve().parents[2]
    codex = _codex_maps(root)
    dolls = _dolls(payload, codex["dolls"])
    fairies = _fairies(payload, codex["fairies"])
    equipment = _equipment(payload)
    sangvis = _sangvis(payload, codex["sangvis"])
    vehicles = _list_at(payload, ("vehicle_info", "vehicle_list", "vehicles"))
    if not any((dolls, fairies, equipment, sangvis, vehicles)):
        raise AndroidCaptureError(
            "Index 响应里没有找到账号列表；顶层字段：" + ", ".join(sorted(map(str, payload)))[:500]
        )
    snapshot = {
        "schema": 1,
        "meta": _meta(payload),
        "dolls": dolls,
        "fairies": fairies,
        "equipment": equipment,
        "sangvis": sangvis,
        "vehicles": vehicles,
        "teams": [],
        "squads": [],
    }
    return snapshot
