"""Rebuild components.json from the verified scheme sheets.

- 归海: full 25-weapon catalog in guihai_weapons.json (183 combos).
- 秋水: 9 components from 主战坦克 - 组件词条 (图1).
- 老吴: 9 components from the plain checklist (图2).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "app" / "data" / "components.json"
CATALOG = ROOT / "app" / "data" / "guihai_weapons.json"

LAOWU = ["火力芯片", "重武芯片", "小型迫击炮", "信号塔", "加农炮", "电磁枪", "护盾发生器", "护甲芯片", "防御芯片"]
QIUSHUI = [
    "火力芯片",
    "重武芯片",
    "精度芯片",
    "鹰眼芯片",
    "小型迫击炮",
    "导弹发射器MK2",
    "烈焰喷射器",
    "车载夜视仪",
    "信号塔",
]
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


def main() -> None:
    guide = json.loads(GUIDE.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    old_requirements = guide.get("requirements") or {}
    requirements = {key: old_requirements.get(key) or {} for key in ("laowu", "qiushui")}
    requirements["laowu"].pop("小迫击炮", None)

    components = []
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
            if weapon["name"] in QIUSHUI:
                schemes.append("qiushui")
            schemes.append("guihai")
            summary = " / ".join(mains + words)
            components.append(
                {
                    "name": weapon["name"],
                    "category": CATEGORY[group["name"]],
                    "words": summary,
                    "schemes": schemes,
                }
            )
    components.extend(EXTRA)

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
                "source": "图1（主战坦克 - 组件词条，9 件）",
            },
        ],
        "catalogs": {"guihai": "guihai_weapons.json"},
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
