"""Build the per-activity Qiushui component catalog.

Input: ``--raw`` JSON produced from 秋水Ameth's Tencent sheets
(see ``Tmp/qiushui_raw.json`` in the working tree).  Output:
``app/data/qiushui_components.json`` plus a human-readable markdown/CSV.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "app" / "data" / "qiushui_components.json"
OUT_MD = ROOT / "docs" / "qiushui_components.md"
OUT_CSV = ROOT / "docs" / "qiushui_components.csv"

ACTIVITY_ORDER = [
    "飓风营救Plus",
    "终焉花海Plus",
    "谜境守卫Plus",
    "三维流形G-4",
    "自画像-厚涂",
    "从潘洛斯阶梯跃下",
    "静默沙盘",
    "铁雨礼赞",
]

ALIASES = {"通用机枪MK-Ⅰ": "通用机枪MK-I", "通用机枪MK-Ⅱ": "通用机枪MK-II"}

REFERENCE = {
    "title": "图1 主战坦克 - 组件词条（旧版总表）",
    "components": [
        {"name": "火力芯片", "stat1": "重武伤害", "stat2": "重武穿甲", "optional": ""},
        {"name": "重武芯片", "stat1": "重武伤害", "stat2": "精度", "optional": ""},
        {"name": "精度芯片", "stat1": "重武伤害", "stat2": "精度", "optional": ""},
        {"name": "鹰眼芯片", "stat1": "重武伤害", "stat2": "重武穿甲", "optional": ""},
        {"name": "小型迫击炮", "stat1": "重武伤害", "stat2": "破防", "optional": "重武支援"},
        {"name": "导弹发射器MK2", "stat1": "重武伤害", "stat2": "重武穿甲", "optional": "弱点突破"},
        {"name": "烈焰喷射器", "stat1": "轻武伤害", "stat2": "破防", "optional": "减益增幅"},
        {"name": "车载夜视仪", "stat1": "暴击概率", "stat2": "破防", "optional": "帕拉蒂斯增幅"},
        {"name": "信号塔", "stat1": "暴击概率", "stat2": "暴击伤害", "optional": "应急增幅"},
    ],
}


def normalize(name: str) -> str:
    name = str(name or "").strip()
    return ALIASES.get(name, name)


def build(raw: list[dict], known: set[str]) -> dict:
    activities: OrderedDict[str, dict] = OrderedDict()
    for rec in raw:
        for block in rec["blocks"]:
            comps = block.get("components") or []
            if len(comps) != 9:
                continue
            names = [normalize(c["name"]) for c in comps]
            if not all(name in known for name in names):
                continue
            if sum(1 for name in names if name.endswith("芯片")) < 2:
                continue
            if sum(1 for c in comps if c["stat1"] and c["stat2"]) < 7:
                continue
            activity = rec["doc"]
            activity_entry = activities.setdefault(
                activity,
                {
                    "id": rec["doc_id"],
                    "name": activity,
                    "url": f"https://docs.qq.com/sheet/{rec['doc_id']}",
                    "tables": [],
                },
            )
            side = "战术人型机甲" if "战术人型机甲" in rec["tab"] else "主战坦克"
            variant = rec["tab"].replace("主战坦克", "").replace("战术人型机甲", "").strip("（）() ")
            table = {
                "id": f"{rec['doc_id']}-{len(activity_entry['tables']) + 1}",
                "side": side,
                "variant": variant or "自用",
                "components": [
                    {
                        "name": normalize(c["name"]),
                        "stat1": c["stat1"],
                        "stat2": c["stat2"],
                        "optional": c["optional"],
                    }
                    for c in comps
                ],
            }
            activity_entry["tables"].append(table)
    ordered = [activities[name] for name in ACTIVITY_ORDER if name in activities]
    ordered += [value for name, value in activities.items() if name not in ACTIVITY_ORDER]
    return {
        "version": "2026-11-25",
        "title": "秋水Ameth 各积分关卡组件词条",
        "source": "秋水Ameth 排行关卡表格合集（腾讯文档，8 个活动的主战坦克 / 战术人型机甲页）",
        "note": "每张表 9 件组件。匹配要求组件名 + 属性词条1 + 属性词条2；任意词条是推荐项，不强制。",
        "coverage": {
            "included": [activity["name"] for activity in ordered],
            "login_required": ["坠入兔洞Plus", "混沌落幕Plus"],
            "no_component_tabs": [
                "虚数迷宫Plus",
                "马蜂窝Plus",
                "秘密涡点Plus",
                "驱雾行动Plus",
                "噩梦迷城Plus",
                "逃亡圣咏",
            ],
        },
        "activities": ordered,
        "reference": REFERENCE,
    }


def write_docs(payload: dict) -> None:
    activities = payload["activities"]
    tables = [table for activity in activities for table in activity["tables"]]
    rows = [component for table in tables for component in table["components"]]
    names = {component["name"] for component in rows}
    lines = [
        "# 秋水Ameth · 各积分关卡组件词条",
        "",
        "来源：秋水Ameth 排行关卡表格合集（腾讯文档）中各活动的「主战坦克 / 战术人型机甲」页。",
        "",
        f"- 活动 **{len(activities)}** 个；表 **{len(tables)}** 张；组件需求行 **{len(rows)}** 条；去重组件 **{len(names)}** 件。",
        "- 每张表固定 9 件：4 个通用芯片 + 5 个其他组件。",
        "- 匹配口径：组件名 + 属性词条1 + 属性词条2；任意词条为推荐项，不强制。",
        "- 旧版「图1 主战坦克 - 组件词条」作为参考表保留在 JSON 的 `reference` 字段。",
        "- 覆盖缺口：坠入兔洞Plus、混沌落幕Plus 的腾讯文档当前要求登录，未能抓取；"
        "虚数迷宫Plus、马蜂窝Plus、秘密涡点Plus、驱雾行动Plus、噩梦迷城Plus、逃亡圣咏 没有组件页。",
        "",
    ]
    for activity in activities:
        lines.append(f"## {activity['name']}")
        lines.append("")
        for table in activity["tables"]:
            lines.append(f"### {table['side']}（{table['variant']}）")
            lines.append("")
            lines.append("| 组件 | 属性词条1 | 属性词条2 | 任意词条 |")
            lines.append("| --- | --- | --- | --- |")
            for component in table["components"]:
                lines.append(
                    f"| {component['name']} | {component['stat1']} | {component['stat2']} | "
                    f"{component['optional'] or '—'} |"
                )
            lines.append("")
    reference = payload.get("reference") or {}
    if reference.get("components"):
        lines.append(f"## {reference.get('title') or '参考表'}")
        lines.append("")
        lines.append("| 组件 | 属性词条1 | 属性词条2 | 任意词条 |")
        lines.append("| --- | --- | --- | --- |")
        for component in reference["components"]:
            lines.append(
                f"| {component['name']} | {component['stat1']} | {component['stat2']} | "
                f"{component['optional'] or '—'} |"
            )
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["活动", "类型", "版本", "组件", "属性词条1", "属性词条2", "任意词条"])
        for activity in activities:
            for table in activity["tables"]:
                for component in table["components"]:
                    writer.writerow(
                        [
                            activity["name"],
                            table["side"],
                            table["variant"],
                            component["name"],
                            component["stat1"],
                            component["stat2"],
                            component["optional"],
                        ]
                    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default=str(ROOT.parent / "Tmp" / "qiushui_raw.json"))
    args = parser.parse_args()
    catalog = json.loads((ROOT / "app" / "data" / "vehicle_components.json").read_text(encoding="utf-8"))
    known = {value["name"] for value in catalog["components"].values()}
    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    payload = build(raw, known)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_docs(payload)
    tables = [table for activity in payload["activities"] for table in activity["tables"]]
    rows = [component for table in tables for component in table["components"]]
    print(
        "activities", len(payload["activities"]),
        "tables", len(tables),
        "rows", len(rows),
        "distinct", len({component["name"] for component in rows}),
    )


if __name__ == "__main__":
    main()
