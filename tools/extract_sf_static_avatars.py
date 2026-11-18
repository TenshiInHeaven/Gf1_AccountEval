"""Extract static Q-version avatars for units without a battle Spine bundle.

Some SWAP Sangvis units only ship a 2D ``*_SS`` sprite (and sometimes an LL
sprite) instead of a Spine skeleton.  Those sprites are still official Q-version
art, so use them as the card avatar rather than a cropped full-body portrait.

Usage (the workspace .sim environment has UnityPy):
  E:\\python\\gf_forge\\.sim\\Scripts\\python.exe tools\\extract_sf_static_avatars.py ^
    --game-root "D:\\...\\GIRLS' FRONTLINE"
"""
from __future__ import annotations

import argparse
from pathlib import Path

import UnityPy
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "avatars" / "sangvis"
BUNDLE_DIR = Path("GrilsFrontLine_Data") / "StreamingAssets" / "Res" / "Pc"

# code -> bundle stem; these are the units whose avatars previously fell back
# to the official portrait crop.
STATIC_CODES = {
    "Striker_SWAP": "strikerswap",
    "Dragoon_SWAP": "dragoonswap",
    "Aegis_SWAP": "aegisswap",
    "Jaeger_SWAP": "jaegerswap",
}


def find_bundle(bundle_dir: Path, stem: str) -> Path | None:
    suffix = f"character{stem}.ab".lower()
    for path in bundle_dir.iterdir():
        if path.is_file() and path.name.lower().endswith(suffix):
            return path
    return None


def sprite_image(bundle: Path) -> Image.Image | None:
    env = UnityPy.load(str(bundle))
    candidates: list[tuple[str, Image.Image]] = []
    for obj in env.objects:
        if obj.type.name != "Sprite":
            continue
        data = obj.read()
        name = str(getattr(data, "m_Name", "") or "")
        try:
            image = data.image.convert("RGBA")
        except Exception:
            continue
        candidates.append((name, image))
    # Prefer the 512px standing/bust sprite used by the in-game UI.
    for name, image in candidates:
        if name.endswith("_SS"):
            return image
    return candidates[0][1] if candidates else None


def normalize(image: Image.Image) -> Image.Image:
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    image = ImageOps.contain(image, (156, 156), Image.LANCZOS)
    canvas = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((160 - image.width) // 2, (160 - image.height) // 2))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", type=Path, required=True)
    args = parser.parse_args()
    bundle_dir = args.game_root / BUNDLE_DIR
    if not bundle_dir.is_dir():
        raise SystemExit(f"bundle directory not found: {bundle_dir}")
    OUT.mkdir(parents=True, exist_ok=True)

    for code, stem in STATIC_CODES.items():
        bundle = find_bundle(bundle_dir, stem)
        if bundle is None:
            print("MISS", code, stem, flush=True)
            continue
        image = sprite_image(bundle)
        if image is None:
            print("NO_SPRITE", code, bundle.name, flush=True)
            continue
        normalize(image).save(OUT / f"{code}.webp", "WEBP", quality=92, method=6)
        print("OK", code, bundle.name, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
