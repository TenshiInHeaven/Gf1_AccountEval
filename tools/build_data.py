"""Build the static codex / alias data used by GF Account Forge.

The project intentionally keeps the game's STC text tables and the
``dataMiner`` exports outside the app.  This script is the reproducible bridge:
it reads those sources once and writes small JSON files into ``app/data``.

Usage:
    python tools/build_data.py --workspace E:\\python\\gf_forge
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.normalize import normalize_name, slugify  # noqa: E402


def read_text_table(path: Path) -> dict[int, str]:
    """Read the game's client text table (``key,value`` per line)."""
    result: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or "," not in line:
            continue
        key, value = line.split(",", 1)
        match = re.search(r"-(\d+)$", key)
        if not match:
            continue
        value = value.split("//")[0].strip()
        if value:
            result[int(match.group(1))] = value
    return result


def load_stc(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["rows"]


def avatar_path(kind: str, code: str) -> str:
    return f"assets/avatars/{kind}/{slugify(code)}.webp"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=ROOT.parent)
    args = parser.parse_args()
    workspace: Path = args.workspace.resolve()

    text_dir = workspace / "Portrait_showcase" / "data" / "text_tables"
    stc_dir = workspace / "dataMiner" / "stc" / "tables"
    derived = workspace / "dataMiner" / "derived"
    out_dir = ROOT / "app" / "data" / "codex"
    out_dir.mkdir(parents=True, exist_ok=True)

    gun_names = read_text_table(text_dir / "gun.txt")
    fairy_names = read_text_table(text_dir / "fairy.txt")
    sangvis_names = read_text_table(text_dir / "sangvis.txt")

    # ------------------------------------------------------------------
    # T-Dolls: canonical catalog from dataMiner + client names
    # ------------------------------------------------------------------
    dolls: list[dict] = []
    with (derived / "doll_catalog_raw.csv").open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            gun_id = int(row["id"])
            code = row["code"].strip()
            if code.endswith("_sangvis"):
                continue
            name = gun_names.get(10_000_000 + gun_id) or row["en_name"] or code
            dolls.append(
                {
                    "id": gun_id,
                    "code": code,
                    "name": name,
                    "en_name": row["en_name"],
                    "type": int(row["type"]) if row["type"].isdigit() else 0,
                    "rank": int(row["rank"]) if row["rank"].isdigit() else 0,
                    "avatar": avatar_path("dolls", code),
                    "kind": "doll",
                    "aliases": sorted({code, row["en_name"], name, code.replace(" ", "")}),
                }
            )
    dolls.sort(key=lambda item: (item["type"], item["rank"], item["id"]))
    (out_dir / "dolls.json").write_text(
        json.dumps(dolls, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # ------------------------------------------------------------------
    # Fairies
    # ------------------------------------------------------------------
    fairies: list[dict] = []
    for row in load_stc(stc_dir / "5115_fairy.json"):
        fairy_id = int(row["id"])
        if fairy_id >= 90_000:  # enemy / theater helper entries
            continue
        code = str(row.get("code") or "").strip()
        name = fairy_names.get(10_000_000 + fairy_id) or code
        fairies.append(
            {
                "id": fairy_id,
                "code": code,
                "name": name,
                "type": int(row.get("type") or 0),
                "category": int(row.get("category") or 0),
                "is_collab": 1_000 <= fairy_id < 9_000,
                "avatar": avatar_path("fairies", code),
                "kind": "fairy",
                "aliases": sorted({code, name, code.replace("_", " ")}),
            }
        )
    fairies.sort(key=lambda item: (item["is_collab"], item["id"]))
    (out_dir / "fairies.json").write_text(
        json.dumps(fairies, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # ------------------------------------------------------------------
    # Sangvis / coalition units
    # ------------------------------------------------------------------
    sangvis: list[dict] = []
    for row in load_stc(stc_dir / "5094_sangvis.json"):
        sf_id = int(row["id"])
        code = str(row.get("code") or "").strip()
        name = sangvis_names.get(10_000_000 + sf_id) or code
        sangvis.append(
            {
                "id": sf_id,
                "code": code,
                "name": name,
                "en_name": row.get("en_name") or code,
                "forces": int(row.get("forces") or 0),
                "type": int(row.get("type") or 0),
                "rank": int(row.get("rank") or 0),
                "avatar": avatar_path("sangvis", code),
                "kind": "sangvis",
                "aliases": sorted({code, row.get("en_name") or "", name}),
            }
        )
    sangvis.sort(key=lambda item: (item["forces"], item["type"], item["id"]))
    # The STC table contains a second row for a few bosses (same code, different
    # event variant).  The codex is keyed by code, so keep the first canonical row.
    seen_sangvis: set[str] = set()
    sangvis = [item for item in sangvis if not (item["code"] in seen_sangvis or seen_sangvis.add(item["code"]))]
    (out_dir / "sangvis.json").write_text(
        json.dumps(sangvis, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # ------------------------------------------------------------------
    # Equipment catalog (needed for target-vs-current equipment counts)
    # ------------------------------------------------------------------
    equip_names = read_text_table(text_dir / "equip.txt")
    equip_items: list[dict] = []
    for row in load_stc(stc_dir / "5038_equip.json"):
        item_id = int(row["id"])
        equip_items.append(
            {
                "id": item_id,
                "name": equip_names.get(10_000_000 + item_id, ""),
                "category": int(row.get("category") or 0),
                "type": int(row.get("type") or 0),
                "code": str(row.get("code") or ""),
                "rank": int(row.get("rank") or 0),
            }
        )
    equip_items.sort(key=lambda item: item["id"])
    (ROOT / "app" / "data" / "equipment_items.json").write_text(
        json.dumps(equip_items, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # ------------------------------------------------------------------
    # Unified alias index (normalized name -> [kind, code])
    # ------------------------------------------------------------------
    aliases: dict[str, list[dict]] = {}
    for kind, rows in (("doll", dolls), ("fairy", fairies), ("sangvis", sangvis)):
        for row in rows:
            keys = {row["name"], row["code"], *row.get("aliases", [])}
            for key in keys:
                if not key:
                    continue
                norm = normalize_name(key)
                if not norm:
                    continue
                aliases.setdefault(norm, [])
                item = {"kind": kind, "code": row["code"], "name": row["name"]}
                if item not in aliases[norm]:
                    aliases[norm].append(item)
    (out_dir / "aliases.json").write_text(
        json.dumps(aliases, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    summary = {
        "dolls": len(dolls),
        "fairies": len(fairies),
        "fairies_collab": sum(1 for item in fairies if item["is_collab"]),
        "sangvis": len(sangvis),
        "equipment_items": len(equip_items),
        "aliases": len(aliases),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
