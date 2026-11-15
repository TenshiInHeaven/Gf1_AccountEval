"""Extract Sangvis battle chibi Spine models from character*spine.ab bundles.

Uses the existing Portrait_showcase extraction/conversion tools (UnityPy +
Spine 2.1 binary -> JSON).  The rendered avatar step is separate
(``tools/render_sf_spine.py``); this script only prepares the Spine assets.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "spine" / "sangvis"
PORTRAIT_TOOLS = ROOT.parent / "Portrait_showcase" / "tools" / "extract"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PORTRAIT_TOOLS))

import common  # noqa: E402
import spine  # noqa: E402
import spine_json  # noqa: E402

SF_STEM_ALIASES = {
    "BossNarciss": "bossnarciss",
    "BossArchitect": "bossarchitect",
    "BossArchitect_Summer": "bossarchitectsummer",
    "BossCerberus": "bosscerberus",
    "BossGager": "bossgager",
    "Agent": "agent",
    "Excutioner": "excutioner",
    "Dreamer_Halloween": "dreamerhalloween",
    "Golyat_Factory": "golyatfactory",
    "Nyto_White_Summer": "nytowhitesummer",
    "RecceCentreSwim_buhuo": "reccecentreswimbuhuo",
    "Vespid_bride": "vespidbride",
    "Guard_chm": "guardchm",
    "GagerSwimwear": "gagerswimwear",
}


def stem_for(code: str) -> str:
    if code in SF_STEM_ALIASES:
        return SF_STEM_ALIASES[code]
    return code.replace("_", "").lower()


def bundle_path(game_root: Path, stem: str) -> Path | None:
    bundle_dir = game_root / "GrilsFrontLine_Data" / "StreamingAssets" / "Res" / "Pc"
    candidates = [f"character{stem}spine.ab"]
    # Several bosses use a ``boss`` prefix in the bundle name even though the
    # unit code does not (Scarecrow, Hunter, Agent, ...).
    if not stem.startswith("boss"):
        candidates.append(f"characterboss{stem}spine.ab")
    lowered = {value.lower() for value in candidates}
    for path in bundle_dir.iterdir():
        if path.is_file() and path.name.lower().endswith(tuple(lowered)):
            return path
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--codes", default="", help="comma-separated SF codes (default: all)")
    args = parser.parse_args()
    codex = json.loads((ROOT / "app" / "data" / "codex" / "sangvis.json").read_text(encoding="utf-8"))
    wanted = {item.strip() for item in args.codes.split(",") if item.strip()}
    if wanted:
        codex = [item for item in codex if item["code"] in wanted]

    OUT.mkdir(parents=True, exist_ok=True)
    tmp_root = OUT.parent / "_tmp"
    spine.SPINE_DIR = OUT
    spine.TMP_ROOT = tmp_root
    spine_json.SPINE_DIR = OUT

    records = []
    for item in codex:
        code = item["code"]
        stem = stem_for(code)
        path = bundle_path(args.game_root, stem)
        record = {"code": code, "stem": stem, "bundle": path.name if path else None}
        if path is None:
            record["status"] = "missing_bundle"
            records.append(record)
            print("MISS", code, stem, flush=True)
            continue
        target = {
            "id": code,
            "gunId": -1,
            "gunCode": code,
            "logical": f"character{stem}spine.ab",
            "file": str(path),
        }
        result = spine.extract_one(target)
        record["extract"] = {key: result.get(key) for key in ("status", "error", "chosen", "pages", "textures")}
        if result.get("status") != "ok":
            record["status"] = result.get("status", "extract_failed")
            records.append(record)
            print("FAIL", code, result.get("status"), result.get("error"), flush=True)
            continue
        try:
            converted = spine_json.convert_one(code)
            record["convert"] = converted
            record["status"] = "ok"
            print("OK", code, converted.get("jsonBytes"), flush=True)
        except Exception as exc:
            record["status"] = "convert_failed"
            record["error"] = f"{type(exc).__name__}: {exc}"
            print("CONVERT FAIL", code, exc, flush=True)
        records.append(record)

    (OUT / "_extract_manifest.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    ok = sum(1 for record in records if record.get("status") == "ok")
    print(json.dumps({"ok": ok, "total": len(records)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
