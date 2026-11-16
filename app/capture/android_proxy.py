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


def _dict_rows(value: Any) -> list[dict]:
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]
    return []


def _list_at(payload: dict, keys: tuple[str, ...]) -> list[dict]:
    wanted = {_norm(key) for key in keys}
    for key, value in payload.items():
        if _norm(key) not in wanted:
            continue
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        # Several CN Index lists are keyed by their own row id:
        #   "equip_with_user_info": {"3826248": {...}, ...}
        #   "fairy_with_user_info": {"95690": {...}, ...}
        rows = _dict_rows(value)
        if rows:
            return rows
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
        rows = value if isinstance(value, list) else _dict_rows(value)
        if not rows:
            continue
        first = rows[0]
        if not isinstance(first, dict):
            continue
        row_keys = {_norm(item) for item in first}
        if row_keys & wanted:
            return [item for item in rows if isinstance(item, dict)]
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
                "level": _int(_get(row, "gun_level", "gunLevel", "level")),
                "exp": _int(_get(row, "gun_exp", "gunExp", "exp", "experience")),
                "favor": _int(_get(row, "favor", "favorability")),
                "team_id": _int(_get(row, "team_id", "teamId")),
                "skin_id": _int(_get(row, "skin_id", "skinId", "skin")),
                "location": _int(_get(row, "location")),
                "number": _int(_get(row, "number", "count")),
                "mod": _int(
                    _get(row, "if_modification", "ifModification", "mod", "mod_level", "modLevel")
                ),
                "skill1": _int(_get(row, "skill1")),
                "skill2": _int(_get(row, "skill2")),
                "equip1": _int(_get(row, "equip1")),
                "equip2": _int(_get(row, "equip2")),
                "equip3": _int(_get(row, "equip3")),
                "equip4": _int(_get(row, "equip4")),
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
        quality = _int(_get(row, "quality_lv", "qualityLv", "quality", "quality_level", "qualityLevel"))
        result.append(
            {
                "id": _int(_get(row, "id", "user_id", "userId", "uid")),
                "code": code,
                "level": _int(_get(row, "fairy_lv", "fairyLv", "level")),
                "exp": _int(_get(row, "fairy_exp", "fairyExp", "exp", "experience")),
                "quality": quality,
                "quality_level": quality,
                "skill_level": _int(
                    _get(row, "skill_lv", "skillLv", "skill_level", "skillLevel", "main_skill_level", "mainSkillLevel")
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
        level = _int(_get(row, "equip_level", "equipLevel", "level"))
        exp = _int(_get(row, "equip_exp", "equipExp", "exp"))
        result.append(
            {
                "id": _int(_get(row, "id", "user_id", "userId", "uid")),
                "gun_id": _int(_get(row, "gun_with_user_id", "gunWithUserId", "gun_id", "gunId")),
                "info_id": _int(info_id),
                "own_number": _int(
                    _get(row, "own_number", "ownNumber", "number", "count", default=1)
                ),
                "level": level,
                "exp": exp,
                "equip_level": level,
                "equip_exp": exp,
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
        resolution = _int(
            _get(row, "sangvis_resolution", "sangvisResolution", "resolution", "resolution_level", "resolutionLevel")
        )
        resolution_level = _int(
            _get(row, "sangvis_resolution_level", "sangvisResolutionLevel", "resolution_level", "resolutionLevel")
        )
        if resolution_level == 0 and resolution:
            resolution_level = resolution
        result.append(
            {
                "id": _int(_get(row, "id", "user_id", "userId", "uid")),
                "info_id": _int(info_id),
                "code": code,
                "level": _int(_get(row, "sangvis_level", "sangvisLevel", "level")),
                "exp": _int(_get(row, "sangvis_exp", "sangvisExp", "exp")),
                "advance": _int(
                    _get(row, "sangvis_advance", "sangvisAdvance", "advance", "advance_level", "advanceLevel")
                ),
                "resolution": resolution,
                "resolution_level": resolution_level,
                "sign": _int(_get(row, "sign")),
                "skin": _int(_get(row, "skin", "skin_id", "skinId")),
                "break_through": _int(
                    _get(row, "break_through", "breakThrough", "break_through_level")
                ),
                "chip1": _get(row, "chip1"),
                "chip2": _get(row, "chip2"),
                "skill1": _int(_get(row, "skill1")),
                "skill2": _int(_get(row, "skill2")),
                "skill3": _int(_get(row, "skill3")),
                "skill_advance": _int(_get(row, "skill_advance", "skillAdvance")),
                "favor": _int(_get(row, "favor")),
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
