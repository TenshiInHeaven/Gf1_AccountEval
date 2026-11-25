"""Build a full component codex (all 141 components, affixes and attachments).

The account snapshot only contains instances the user owns.  This codex is a
local data asset built from the game's STC/text tables so the PWA/Android app
can browse every component, every possible affix and every roll attachment
without needing an imported JSON.

    python tools/build_component_codex.py --workspace E:\\python\\gf_forge
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "app" / "data" / "vehicle_components.json"
GUIDE = ROOT / "app" / "data" / "components.json"
OUT = ROOT / "app" / "data" / "component_codex.json"

STAT_NAMES = {
    "heavy_damage": "重武伤害",
    "light_damage": "轻武伤害",
    "reload": "装填",
    "atk_speed": "攻速",
    "precision": "精度",
    "hit": "命中",
    "armor": "护甲",
    "dodge": "回避",
    "crit_rate": "暴击概率",
    "crit_damage": "暴击伤害",
    "H_armor_piercing": "重武穿甲",
    "L_armor_piercing": "轻武穿甲",
    "def_break": "破防",
    "energy": "蓄能",
    "energy_bak": "蓄能备份",
}


def text_table(folder: Path, name: str) -> dict[str, str]:
    path = folder / name
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) >= 2:
                result[row[0]] = row[1]
    return result


def rows(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["rows"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=r"E:\python\gf_forge")
    args = parser.parse_args()
    workspace = Path(args.workspace)
    stc = workspace / "dataMiner" / "stc" / "tables"
    text = workspace / "Portrait_showcase" / "data" / "text_tables"

    base = json.loads(BASE.read_text(encoding="utf-8"))
    guide = json.loads(GUIDE.read_text(encoding="utf-8"))
    skill_names = base.get("skill_names") or {}
    roll_names = base.get("roll_names") or {}
    types = base.get("types") or {}

    component_rows = {str(row["id"]): row for row in rows(stc / "5218_vehicle_component.json")}
    roll_rows = {str(row["id"]): row for row in rows(stc / "5216_vehicle_component_roll.json")}
    group_text = text_table(text, "vehicle_component_group.txt")
    roll_text = text_table(text, "vehicle_component_roll.txt")

    schemes: dict[str, list[str]] = {}
    for item in guide.get("components") or []:
        schemes[str(item.get("name") or "")] = list(item.get("schemes") or [])

    roll_types: dict[str, dict] = {}
    for roll_id, row in roll_rows.items():
        stats = []
        for key, label in STAT_NAMES.items():
            weight = int(row.get(key) or 0)
            if weight:
                stats.append({"key": key, "name": label, "weight": weight})
        attachments = []
        seen_skills = set()
        for group_key in ("skill_group1", "skill_group2", "skill_group3"):
            weight_default = int(row.get(f"{group_key}_weight") or 0)
            for entry in str(row.get(group_key) or "").split(";"):
                if "," not in entry:
                    continue
                skill_id, weight = entry.split(",", 1)
                skill_id = skill_id.strip()
                if not skill_id or skill_id in seen_skills:
                    continue
                seen_skills.add(skill_id)
                attachments.append(
                    {
                        "id": skill_id,
                        "name": skill_names.get(skill_id, skill_id),
                        "weight": int(weight or weight_default or 0),
                        "group": group_key,
                    }
                )
        roll_types[roll_id] = {
            "id": roll_id,
            "name": roll_text.get(f"vehicle_component_roll-{10000000 + int(roll_id)}", roll_id),
            "description": "",
            "stats": stats,
            "attachments": attachments,
        }

    codex = []
    for component_id, meta in base.get("components", {}).items():
        row = component_rows.get(component_id) or {}
        group_id = str(row.get("group") or "")
        group_name = group_text.get(f"vehicle_component_group-{10000000 + int(group_id)}", "") if group_id else ""
        roll_id = str(row.get("att_roll") or "")
        roll = roll_types.get(roll_id) or {}
        main_skill_id = str(row.get("skill") or "").split(":")[-1] if row.get("skill") else ""
        main_skill = skill_names.get(main_skill_id, main_skill_id) if main_skill_id else ""
        codex.append(
            {
                "id": component_id,
                "name": meta.get("name", component_id),
                "code": row.get("code") or "",
                "type": int(meta.get("type") or 0),
                "type_name": meta.get("type_name") or types.get(str(meta.get("type") or 0), ""),
                "rank": int(meta.get("rank") or row.get("rank") or 0),
                "group": group_id,
                "group_name": group_name,
                "unlock_lv": row.get("unlock_lv") or "",
                "att_roll": roll_id,
                "roll_name": roll.get("name", ""),
                "stats": roll.get("stats", []),
                "attachments": roll.get("attachments", []),
                "main_skill": main_skill,
                "schemes": schemes.get(str(meta.get("name") or ""), []),
            }
        )
    codex.sort(key=lambda item: (item["type"], -item["rank"], item["name"]))

    payload = {
        "version": "2026-11-25",
        "source": "dataMiner STC 5216/5218/5219/5223 + vehicle_component 文本表；全量组件词条与配件",
        "types": types,
        "stats": STAT_NAMES,
        "roll_types": roll_types,
        "components": codex,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT.name}: {len(codex)} components, {len(roll_types)} roll types, {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
