"""Build the static PWA data/assets from the Python app sources.

The web app is intentionally static: it reads the same codex/tier/equipment/
component JSON and the same WebP avatars as the Qt app.  Run this after
changing any data file:

    python tools/build_web.py
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DATA = ROOT / "app" / "data"
VERSION = re.search(r'__version__ = "([^"]+)"', (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")).group(1)

JSON_FILES = [
    ("codex/dolls.json", "codex/dolls.json"),
    ("codex/fairies.json", "codex/fairies.json"),
    ("codex/sangvis.json", "codex/sangvis.json"),
    ("tierlists/dolls.json", "tierlists/dolls.json"),
    ("tierlists/fairies.json", "tierlists/fairies.json"),
    ("tierlists/sangvis.json", "tierlists/sangvis.json"),
    ("equipment_items.json", "equipment_items.json"),
    ("equipment_targets.json", "equipment_targets.json"),
    ("equipment_activities.json", "equipment_activities.json"),
    ("components.json", "components.json"),
    ("guihai_weapons.json", "guihai_weapons.json"),
    ("qiushui_components.json", "qiushui_components.json"),
    ("vehicle_components.json", "vehicle_components.json"),
    ("component_codex.json", "component_codex.json"),
    ("sample_account.json", "sample_account.json"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-avatars", action="store_true")
    args = parser.parse_args()

    for src_name, dst_name in JSON_FILES:
        src = DATA / src_name
        dst = WEB / "data" / dst_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

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
    avatar_count = sum(1 for _ in (WEB / "assets" / "avatars").rglob("*.webp")) if (WEB / "assets" / "avatars").is_dir() else 0

    data_files = sorted(
        path.relative_to(WEB).as_posix()
        for path in (WEB / "data").rglob("*.json")
        if path.name not in {"core.json", "build_info.json"}
    )
    core = [
        "./index.html",
        "./styles.css",
        "./app.js",
        "./modules.js",
        "./manifest.webmanifest",
        "./icons/icon-192.png",
        "./icons/icon-512.png",
        *[f"./{name}" for name in data_files],
    ]
    (WEB / "data" / "core.json").write_text(json.dumps(core, ensure_ascii=False, indent=1), encoding="utf-8")

    summary = {
        "version": VERSION,
        "web": "web",
        "avatars": avatar_count,
        "data_files": len(data_files),
        "core_files": len(core),
    }
    (WEB / "data" / "build_info.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
