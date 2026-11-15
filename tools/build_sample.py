"""Create the bundled demo snapshot from the 2026-11-07 dataMiner export.

This is real account data captured from the PC client (roster / fairies /
equipment / teams).  Sangvis entries are the 10 coalition units observed in the
saved echelons; a live XLua extraction provides the complete ``listSangvisGun``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def as_int(value, default=0):
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=ROOT.parent)
    args = parser.parse_args()
    derived = args.workspace.resolve() / "dataMiner" / "derived"
    out = ROOT / "app" / "data" / "sample_account.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    roster = load_json(derived / "player_roster_lua_20261107.json")
    fairies = load_json(derived / "player_fairies_lua_20261107.json")
    equipment = load_json(derived / "player_equipment_lua_20261107.json")
    teams = load_json(derived / "player_teams_lua_20261107.json")
    squads = load_json(derived / "player_squads_lua_20261107.json")
    vehicles = load_json(derived / "player_vehicles_lua_20261107.json")

    dolls = []
    for row in roster:
        dolls.append(
            {
                "uid": as_int(row.get("uid")),
                "code": row.get("code", ""),
                "level": as_int(row.get("level")),
                "exp": as_int(row.get("exp")),
                "favor": as_int(row.get("favor")),
                "team_id": as_int(row.get("teamId")),
                "skin_id": as_int(row.get("skinId")),
                "location": as_int(row.get("location")),
                "number": as_int(row.get("number")),
                "mod": as_int(row.get("mod")),
            }
        )

    fairy_rows = []
    for row in fairies:
        fairy_rows.append(
            {
                "id": as_int(row.get("id")),
                "code": row.get("code", ""),
                "level": as_int(row.get("level")),
                "exp": as_int(row.get("exp")),
                "quality": as_int(row.get("qualityLevel")),
                "skill_level": as_int(row.get("mainSkillLevel")),
                "mod": as_int(row.get("mod")),
                "team_id": as_int(row.get("teamId")),
                "equip_id": as_int(row.get("equipId")),
                "is_collect": str(row.get("isCollect", "false")).lower() == "true",
            }
        )

    equip_rows = []
    for row in equipment:
        equip_rows.append(
            {
                "id": as_int(row.get("id")),
                "gun_id": as_int(row.get("gunId")),
                "info_id": as_int(row.get("infoId")),
                "own_number": as_int(row.get("ownNumber")),
                "level": as_int(row.get("equip_level")),
                "exp": as_int(row.get("equip_exp")),
            }
        )

    # Only the coalition units that appear in saved echelons are observable
    # from this snapshot.  The live extractor fills the full list.
    seen = {}
    for row in teams:
        if row.get("class") != "融合势力":
            continue
        code = row.get("code", "")
        if not code:
            continue
        item = seen.setdefault(
            code,
            {
                "code": code,
                "level": as_int(row.get("level")),
                "advance": 0,
                "resolution_level": 0,
                "uid": as_int(row.get("uid")),
                "team_id": as_int(row.get("teamId")),
                "source": "team_observation",
            },
        )
        item["level"] = max(item["level"], as_int(row.get("level")))
    sangvis = sorted(seen.values(), key=lambda item: (-item["level"], item["code"]))

    snapshot = {
        "schema": 1,
        "meta": {
            "uid": "SAMPLE-20261107",
            "nickname": "示例账号",
            "level": 209,
            "source": "dataMiner 2026-11-07 XLua 导出",
            "captured_at": "2026-11-07T00:00:00+08:00",
            "game": "少女前线 PC（国服）",
            "note": "真实仓库/妖精/装备数据；融合势力仅含编队中出现的单位。",
        },
        "dolls": dolls,
        "fairies": fairy_rows,
        "equipment": equip_rows,
        "sangvis": sangvis,
        "teams": teams,
        "squads": squads,
        "vehicles": vehicles,
    }
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out),
                "dolls": len(dolls),
                "fairies": len(fairy_rows),
                "equipment": len(equip_rows),
                "sangvis": len(sangvis),
                "teams": len(teams),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
