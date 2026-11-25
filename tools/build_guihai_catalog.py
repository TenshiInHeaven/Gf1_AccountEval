"""Build the full Guihai vehicle-weapon catalog from the 2025-11-16 sheet.

Source: account_evaluate/机动装甲武器.png
The sheet's columns are 主词条 / 副词条1 / 副词条2 (weapons) or 词条1 / 词条2
(chips).  Every recommended row becomes one combo of words that a component
must carry.  The catalog is committed as JSON so the app never needs OCR.
"""
from __future__ import annotations

import csv
import json
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "app" / "data" / "guihai_weapons.json"
OUT_MD = ROOT / "docs" / "guihai_weapons.md"
OUT_CSV = ROOT / "docs" / "guihai_weapons.csv"

HEAVY_3 = [["重武伤害", "精度"], ["重武伤害", "破防"], ["重武伤害", "重武穿甲"]]
LIGHT_4 = [["轻武伤害", "攻速"], ["轻武伤害", "破防"], ["轻武伤害", "轻武穿甲"], ["轻武伤害", "命中"]]
FUNC_5 = [
    ["破防", "重武穿甲"],
    ["破防", "轻武穿甲"],
    ["暴击概率", "暴击伤害"],
    ["暴击概率", "轻武穿甲"],
    ["暴击概率", "破防"],
]
FUNC_4 = [
    ["破防", "重武穿甲"],
    ["破防", "轻武穿甲"],
    ["暴击概率", "暴击伤害"],
    ["暴击概率", "破防"],
]
PROT_6 = [
    ["护甲", "暴击概率"],
    ["护甲", "破防"],
    ["护甲", "暴击伤害"],
    ["护甲", "回避"],
    ["暴击概率", "暴击伤害"],
    ["暴击概率", "破防"],
]

WEAPONS = OrderedDict(
    [
        (
            "重武",
            [
                {
                    "name": "导弹发射器MK2",
                    "mains": [
                        ("重武护盾", HEAVY_3),
                        ("机械特化", HEAVY_3),
                        ("有甲特化", HEAVY_3),
                        ("多编特化", HEAVY_3),
                        ("重武支援", HEAVY_3),
                        ("弱点突破", HEAVY_3),
                    ],
                },
                {
                    "name": "小型迫击炮",
                    "mains": [
                        ("重武护盾", HEAVY_3),
                        ("应急护盾", HEAVY_3),
                        ("机械特化", HEAVY_3),
                        ("有甲特化", HEAVY_3),
                        ("多编特化", HEAVY_3),
                        ("重武支援", HEAVY_3),
                        ("弱点突破", HEAVY_3),
                    ],
                },
                {
                    "name": "激光武器",
                    "mains": [
                        ("机械特化", HEAVY_3),
                        ("有甲特化", HEAVY_3),
                    ],
                },
                {
                    "name": "榴弹发射器",
                    "mains": [
                        (
                            "重武护盾",
                            [
                                ["重武伤害", "精度"],
                                ["重武伤害", "破防"],
                                ["重武伤害", "重武穿甲"],
                                ["重武伤害", "装填"],
                            ],
                        )
                    ],
                },
                {
                    "name": "导弹发射器MK1",
                    "mains": [("重武护盾", HEAVY_3)],
                },
            ],
        ),
        (
            "轻武",
            [
                {
                    "name": "反装甲狙击枪",
                    "mains": [
                        ("减益增幅", LIGHT_4),
                        ("应急增幅", LIGHT_4),
                        ("单编特化", LIGHT_4),
                        ("轻武支援", LIGHT_4),
                    ],
                },
                {
                    "name": "烈焰喷射器",
                    "mains": [
                        ("减益增幅", [["轻武伤害", "破防"], ["轻武伤害", "轻武穿甲"]]),
                        ("应急增幅", [["轻武伤害", "破防"], ["轻武伤害", "轻武穿甲"]]),
                    ],
                },
                {"name": "轻型速射电磁枪", "mains": [("单编特化", LIGHT_4)]},
                {
                    "name": "车载霰弹枪",
                    "mains": [
                        (
                            "人形特化",
                            [
                                ["轻武伤害", "破防"],
                                ["轻武伤害", "轻武穿甲"],
                                ["轻武伤害", "命中"],
                            ],
                        )
                    ],
                },
                {"name": "重机枪", "mains": [("急速强化", LIGHT_4)]},
            ],
        ),
        (
            "功能",
            [
                {
                    "name": "车载夜视仪",
                    "mains": [
                        ("正规军增幅", FUNC_5),
                        ("帕拉蒂斯增幅", FUNC_5),
                        ("护盾预防", FUNC_5),
                    ],
                },
                {
                    "name": "相控阵雷达",
                    "mains": [
                        ("正规军增幅", FUNC_5),
                        ("帕拉蒂斯增幅", FUNC_5),
                        ("护盾预防", FUNC_5),
                    ],
                },
                {
                    "name": "信号塔",
                    "mains": [
                        ("减益增幅", FUNC_4),
                        ("应急增幅", FUNC_4),
                        ("精英增幅", FUNC_4),
                    ],
                },
            ],
        ),
        (
            "防护",
            [
                {
                    "name": "迷彩网",
                    "mains": [
                        ("护盾预防", PROT_6),
                        ("应急护盾", PROT_6),
                        ("护盾增伤", PROT_6),
                    ],
                },
                {
                    "name": "防护发生器",
                    "mains": [
                        ("连携减伤", PROT_6),
                        ("应急护盾", PROT_6),
                    ],
                },
                {"name": "爆炸反应装甲", "mains": [("护盾增伤", PROT_6)]},
                {"name": "顶部格栅装甲", "mains": [("护盾增伤", PROT_6)]},
            ],
        ),
        (
            "芯片",
            [
                {"name": "重武芯片", "combos": [["重武伤害", "重武穿甲"], ["重武伤害", "精度"]]},
                {"name": "轻武芯片", "combos": [["轻武伤害", "攻速"], ["轻武伤害", "轻武穿甲"]]},
                {"name": "火力芯片", "combos": [["重武伤害", "轻武伤害"], ["重武伤害", "重武穿甲"]]},
                {"name": "精度芯片", "combos": [["重武伤害", "重武穿甲"], ["重武伤害", "精度"]]},
                {"name": "鹰眼芯片", "combos": [["重武伤害", "重武穿甲"], ["重武伤害", "轻武伤害"]]},
                {"name": "护甲芯片", "combos": [["护甲", "回避"], ["护甲", "精度"], ["护甲", "命中"]]},
                {"name": "防御芯片", "combos": [["护甲", "回避"], ["护甲", "命中"]]},
                {"name": "攻速芯片", "combos": [["轻武伤害", "攻速"]]},
            ],
        ),
    ]
)


def build_payload() -> dict:
    groups = []
    index = 0
    for group_name, weapons in WEAPONS.items():
        group_weapons = []
        for weapon in weapons:
            out = {"name": weapon["name"]}
            if "mains" in weapon:
                out["mains"] = [
                    {"word": word, "combos": [list(combo) for combo in combos]} for word, combos in weapon["mains"]
                ]
            else:
                out["combos"] = [list(combo) for combo in weapon["combos"]]
            group_weapons.append(out)
            index += 1
        groups.append({"name": group_name, "weapons": group_weapons})
    return {
        "version": "2026-11-25",
        "title": "归海临渊 · 机动装甲武器词条全表",
        "source": "机动装甲武器.png（2025/11/16）",
        "scheme": "guihai",
        "note": "主词条 / 副词条1 / 副词条2 逐行抄录；芯片只有词条1 / 词条2。组件必须同时拥有整条组合的全部词条才算命中。",
        "groups": groups,
    }


def flatten(payload: dict) -> list[dict]:
    rows = []
    seq = 0
    for group in payload["groups"]:
        for weapon in group["weapons"]:
            if "mains" in weapon:
                for main in weapon["mains"]:
                    for combo in main["combos"]:
                        seq += 1
                        words = [main["word"]] + list(combo)
                        rows.append(
                            {
                                "id": f"gh-{seq:03d}",
                                "group": group["name"],
                                "weapon": weapon["name"],
                                "main": main["word"],
                                "words": words,
                            }
                        )
            else:
                for combo in weapon["combos"]:
                    seq += 1
                    rows.append(
                        {
                            "id": f"gh-{seq:03d}",
                            "group": group["name"],
                            "weapon": weapon["name"],
                            "main": "",
                            "words": list(combo),
                        }
                    )
    return rows


def main() -> None:
    payload = build_payload()
    rows = flatten(payload)
    weapon_count = sum(len(group["weapons"]) for group in payload["groups"])
    main_count = sum(
        1
        for group in payload["groups"]
        for weapon in group["weapons"]
        for _ in weapon.get("mains", [])
    )
    combo_count = len(rows)
    print(f"weapons={weapon_count} mains={main_count} combos={combo_count}")
    assert combo_count == 183, combo_count
    assert weapon_count == 25, weapon_count
    ids = [row["id"] for row in rows]
    assert len(set(ids)) == len(ids)
    keys = {(row["weapon"], tuple(row["words"])) for row in rows}
    assert len(keys) == len(rows)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 归海临渊 · 机动装甲武器词条全表",
        "",
        "来源：`机动装甲武器.png`（2025/11/16，归海临渊一图流）。",
        "",
        f"- 组件 **{weapon_count}** 件；主词条方案 **{main_count}** 条（{len({row['main'] for row in rows if row['main']})} 种主词条）；词条组合 **{combo_count}** 条。",
        "- 每条组合列出「主词条 + 副词条1 + 副词条2」，组件必须同时拥有这些词条才算命中；芯片只有两条词条。",
        "- 对照：秋水Ameth 的主战坦克组件表只有 **9** 件，老吴仙人 **9** 件（见 `components.json`）。",
        "- 数据文件：`app/data/guihai_weapons.json`；本页由 `tools/build_guihai_catalog.py` 生成。",
        "",
    ]
    for group in payload["groups"]:
        lines.append(f"## {group['name']}")
        lines.append("")
        for weapon in group["weapons"]:
            if "mains" in weapon:
                total = sum(len(main["combos"]) for main in weapon["mains"])
                lines.append(f"### {weapon['name']}（{len(weapon['mains'])} 个主词条 / {total} 条）")
                lines.append("")
                lines.append("| 主词条 | 副词条1 | 副词条2 |")
                lines.append("| --- | --- | --- |")
                for main in weapon["mains"]:
                    for combo in main["combos"]:
                        cells = [main["word"]] + list(combo)
                        while len(cells) < 3:
                            cells.append("—")
                        lines.append("| " + " | ".join(cells) + " |")
                lines.append("")
            else:
                lines.append(f"### {weapon['name']}（{len(weapon['combos'])} 条）")
                lines.append("")
                lines.append("| 词条1 | 词条2 |")
                lines.append("| --- | --- |")
                for combo in weapon["combos"]:
                    lines.append("| " + " | ".join(combo) + " |")
                lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "组", "组件", "主词条", "词条组合", "词条数"])
        for row in rows:
            writer.writerow(
                [
                    row["id"],
                    row["group"],
                    row["weapon"],
                    row["main"],
                    " + ".join(row["words"]),
                    len(row["words"]),
                ]
            )
    print("wrote", OUT_JSON, OUT_MD, OUT_CSV)


if __name__ == "__main__":
    main()
