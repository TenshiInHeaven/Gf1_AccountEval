"""Rebuild components.json from the verified scheme sheets.

- 归海: full 25-weapon catalog in guihai_weapons.json (183 combos).
- 秋水: union of every per-activity table in qiushui_components.json.
- 老吴: 9 components from the plain checklist (图2).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "app" / "data" / "components.json"
CATALOG = ROOT / "app" / "data" / "guihai_weapons.json"
QIUSHUI = ROOT / "app" / "data" / "qiushui_components.json"

LAOWU = ["火力芯片", "重武芯片", "小型迫击炮", "信号塔", "加农炮", "电磁枪", "护盾发生器", "护甲芯片", "防御芯片"]
CATEGORY = {
    "重武": "重武器",
    "轻武": "轻武器",
    "功能": "功能组件",
    "防护": "防护组件",
    "芯片": "通用组件",
}
EXTRA = [
    {"name": "加农炮", "category": "重武器", "words": "重武护盾；重武伤害", "schemes": ["laowu"]},
    {"name": "电磁枪", "category": "其他组件", "words": "单编增幅", "schemes": ["laowu"]},
    {"name": "护盾发生器", "category": "防护组件", "words": "护盾偏折", "schemes": ["laowu"]},
]
QIUSHUI_CATEGORY = {
    "回避芯片": "通用组件",
    "旋转炮台": "轻武器",
    "装甲加农炮": "重武器",
    "通用机枪MK-I": "轻武器",
    "干扰枪": "功能组件",
}


def main() -> None:
    guide = json.loads(GUIDE.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    qiushui = json.loads(QIUSHUI.read_text(encoding="utf-8"))

    qiushui_names: list[str] = []
    for activity in qiushui.get("activities") or []:
        for table in activity.get("tables") or []:
            for component in table.get("components") or []:
                name = str(component.get("name") or "")
                if name and name not in qiushui_names:
                    qiushui_names.append(name)

    old_requirements = guide.get("requirements") or {}
    requirements = {"laowu": old_requirements.get("laowu") or {}}
    requirements["laowu"].pop("小迫击炮", None)

    components = []
    seen = set()
    for group in catalog["groups"]:
        for weapon in group["weapons"]:
            words = []
            mains = []
            for main in weapon.get("mains") or []:
                if main["word"] not in mains:
                    mains.append(main["word"])
                for combo in main["combos"]:
                    for word in combo:
                        if word not in words:
                            words.append(word)
            for combo in weapon.get("combos") or []:
                for word in combo:
                    if word not in words:
                        words.append(word)
            schemes = []
            if weapon["name"] in LAOWU:
                schemes.append("laowu")
            if weapon["name"] in qiushui_names:
                schemes.append("qiushui")
            schemes.append("guihai")
            components.append(
                {
                    "name": weapon["name"],
                    "category": CATEGORY[group["name"]],
                    "words": " / ".join(mains + words),
                    "schemes": schemes,
                }
            )
            seen.add(weapon["name"])
    for item in EXTRA:
        if item["name"] in seen:
            continue
        entry = dict(item)
        entry["schemes"] = list(item["schemes"])
        if item["name"] in qiushui_names:
            entry["schemes"].append("qiushui")
        components.append(entry)
        seen.add(item["name"])
    for name in qiushui_names:
        if name in seen:
            continue
        components.append(
            {
                "name": name,
                "category": QIUSHUI_CATEGORY.get(name, "其他组件"),
                "words": "秋水各积分关卡组件",
                "schemes": ["qiushui"],
            }
        )
        seen.add(name)

    payload = {
        "version": "2026-11-25",
        "title": "机动装甲组件方案总表",
        "schemes": [
            {
                "id": "laowu",
                "name": "老吴仙人的咸鱼养成法",
                "short": "老吴",
                "source": "图2（主战坦克组件清单，9 件）",
            },
            {
                "id": "guihai",
                "name": "归海临渊的一图流",
                "short": "归海",
                "source": "图3 / 机动装甲武器.png（25 件 / 183 条词条组合）",
            },
            {
                "id": "qiushui",
                "name": "秋水Ameth的不同积分关卡养成集成",
                "short": "秋水",
                "source": "腾讯文档 8 个活动 / 21 张 主战坦克·战术人型机甲 表（29 件组件）",
            },
        ],
        "catalogs": {"guihai": "guihai_weapons.json", "qiushui": "qiushui_components.json"},
        "components": components,
        "requirements": requirements,
    }

    GUIDE.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("components:", len(components))
    for scheme in ("laowu", "qiushui", "guihai"):
        names = [item["name"] for item in components if scheme in item["schemes"]]
        print(scheme, len(names), names)


if __name__ == "__main__":
    main()
