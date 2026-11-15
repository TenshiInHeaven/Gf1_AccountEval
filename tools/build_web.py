"""Build the static PWA data/assets from the Python app sources.

The web app is intentionally static: it reads the same tier/codex JSON and the
same WebP avatars as the Qt app.  Run this after changing codex/tier data:

    python tools/build_web.py
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def copy_json(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-avatars", action="store_true")
    args = parser.parse_args()

    data = ROOT / "app" / "data"
    for name in ("dolls.json", "fairies.json", "sangvis.json"):
        copy_json(data / "codex" / name, WEB / "data" / "codex" / name)
    for name in ("dolls.json", "fairies.json", "sangvis.json"):
        copy_json(data / "tierlists" / name, WEB / "data" / "tierlists" / name)
    copy_json(data / "equipment_items.json", WEB / "data" / "equipment_items.json")
    copy_json(data / "equipment_targets.json", WEB / "data" / "equipment_targets.json")
    copy_json(data / "sample_account.json", WEB / "data" / "sample_account.json")

    icon_src = ROOT / "assets" / "app_icon.png"
    icon_dir = WEB / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    if icon_src.is_file():
        image = Image.open(icon_src).convert("RGBA")
        for size in (192, 512):
            image.resize((size, size), Image.LANCZOS).save(icon_dir / f"icon-{size}.png")

    if not args.skip_avatars:
        src = ROOT / "assets" / "avatars"
        dst = WEB / "assets" / "avatars"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        avatar_count = sum(1 for _ in dst.rglob("*.webp"))
    else:
        avatar_count = sum(1 for _ in (WEB / "assets" / "avatars").rglob("*.webp")) if (WEB / "assets" / "avatars").is_dir() else 0

    summary = {
        "web": "web",
        "avatars": avatar_count,
        "data_files": len(list((WEB / "data").rglob("*.json"))),
    }
    (WEB / "data" / "build_info.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
