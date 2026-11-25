"""Build the Android WebView assets from the static PWA.

    python tools/build_web.py
    python tools/build_android_assets.py
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
ANDROID = ROOT / "android"
ASSETS = ANDROID / "app" / "src" / "main" / "assets" / "www"
RES = ANDROID / "app" / "src" / "main" / "res"
ICON = ROOT / "assets" / "app_icon.png"

DENSITIES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-icons", action="store_true")
    args = parser.parse_args()

    if ASSETS.exists():
        shutil.rmtree(ASSETS)
    shutil.copytree(WEB, ASSETS)

    if not args.skip_icons and ICON.is_file():
        image = Image.open(ICON).convert("RGBA")
        for folder, size in DENSITIES.items():
            target = RES / folder
            target.mkdir(parents=True, exist_ok=True)
            image.resize((size, size), Image.LANCZOS).save(target / "ic_launcher.png")

    avatars = sum(1 for _ in ASSETS.rglob("*.webp"))
    files = sum(1 for _ in ASSETS.rglob("*") if _.is_file())
    print(f"android assets: {ASSETS} ({files} files, {avatars} avatars)")
    print(f"            size: {sum(p.stat().st_size for p in ASSETS.rglob('*') if p.is_file()) / 1024 / 1024:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
