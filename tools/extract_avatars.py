"""Extract T-Doll / fairy / Sangvis head icons from the local GFL PC bundles.

Requires UnityPy (the workspace ``.sim`` Python already has it).  Run from the
project root or pass --workspace / --game-root explicitly:

    E:\\python\\gf_forge\\.sim\\Scripts\\python.exe tools/extract_avatars.py ^
        --workspace E:\\python\\gf_forge ^
        --game-root "D:\\...\\GIRLS' FRONTLINE"

The generated PNGs are checked into ``assets/avatars`` so the Qt app itself has
no UnityPy dependency.  When a true head icon is unavailable, the script falls
back to a bust crop of the character's default portrait (from Portrait_showcase)
and finally to a generated initial tile.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.normalize import normalize_name, slugify  # noqa: E402

SIZE = 160
ALIASES = {
    "Excutioner": "Executioner",
    "BossArchitect": "BossArchitect",
    "BossArchitect_Summer": "BossArchitect",
    "BossGager": "BossGager",
}

# Event/variant SF units reuse the base character's portrait when the event
# skin is not present in Portrait_showcase.  The face remains the correct
# character even if the outfit differs.
SF_PORTRAIT_ALIASES = {
    "BossArchitect_Summer": "BossArchitect",
    "Scarecrow_SpringFes": "Scarecrow",
    "Destroyer_Christmas": "Destroyer",
    "Excutioner_Halloween": "Excutioner",
    "Dreamer_Halloween": "Dreamer",
    "Nyto_White_Summer": "Nyto_white",
}


def find_bundle(root: Path, suffix: str) -> Path | None:
    for path in root.iterdir():
        if path.is_file() and path.name.lower().endswith(suffix.lower()):
            return path
    return None


def sprite_index(env) -> dict[str, object]:
    result: dict[str, object] = {}
    for obj in env.objects:
        if obj.type.name != "Sprite":
            continue
        try:
            data = obj.read()
        except Exception:
            continue
        name = getattr(data, "m_Name", "") or ""
        if not name:
            continue
        result.setdefault(name, data)
    return result


def render_sprite(sprite) -> Image.Image | None:
    try:
        image = sprite.image
    except Exception:
        return None
    if image is None:
        return None
    image = image.convert("RGBA")
    image.thumbnail((SIZE, SIZE), Image.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((SIZE - image.width) // 2, (SIZE - image.height) // 2))
    return canvas


def render_portrait(path: Path) -> Image.Image | None:
    """Turn a full-body transparent thumbnail into a square bust crop."""
    try:
        image = Image.open(path).convert("RGBA")
    except Exception:
        return None
    # Trim fully transparent margins first, then keep the top ~42% of the
    # character.  This produces a head/shoulders avatar instead of a full-body
    # miniature, and works for both humanoid bosses and mech units.
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    width, height = image.size
    image = image.crop((0, 0, width, max(1, int(height * 0.42))))
    image = ImageOps.fit(image, (SIZE, SIZE), method=Image.LANCZOS, centering=(0.5, 0.15))
    return image


def placeholder(label: str, kind: str) -> Image.Image:
    palette = {
        "dolls": ((42, 48, 60), (242, 193, 78)),
        "fairies": ((40, 52, 50), (111, 174, 123)),
        "sangvis": ((52, 40, 44), (233, 138, 60)),
    }
    bg, fg = palette.get(kind, ((42, 48, 60), (240, 240, 240)))
    image = Image.new("RGBA", (SIZE, SIZE), (*bg, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((3, 3, SIZE - 3, SIZE - 3), radius=24, outline=(*fg, 130), width=2)
    text = (label or "?")[:2]
    font = None
    for candidate in ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"):
        try:
            font = ImageFont.truetype(candidate, 50)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(
        ((SIZE - (box[2] - box[0])) / 2, (SIZE - (box[3] - box[1])) / 2 - 6),
        text,
        fill=(*fg, 255),
        font=font,
    )
    return image


def best_exact(sprite_names: list[str], code: str) -> str | None:
    target = normalize_name(code)
    for name in sprite_names:
        if normalize_name(name) == target:
            return name
    return None


def best_head(sprite_names: list[str], code: str) -> str | None:
    target = normalize_name(code)
    exact = [name for name in sprite_names if normalize_name(name) == target]
    if exact:
        return sorted(exact, key=len)[0]
    prefixed = [
        name
        for name in sprite_names
        if normalize_name(name).startswith(target)
        and len(normalize_name(name)) > len(target)
    ]
    if prefixed:
        return sorted(prefixed, key=lambda name: (len(normalize_name(name)), name))[0]
    contained = [name for name in sprite_names if target and target in normalize_name(name)]
    if contained:
        return sorted(contained, key=lambda name: (len(normalize_name(name)), name))[0]
    return None


def best_fairy(sprite_names: list[str], code: str) -> str | None:
    target = normalize_name(code)
    exact = [name for name in sprite_names if normalize_name(name) == target]
    if exact:
        return exact[0]
    candidates = [
        name
        for name in sprite_names
        if normalize_name(name).startswith(target + "_")
        or normalize_name(name).startswith(target)
    ]
    if not candidates:
        return None

    def rank(name: str) -> tuple[int, int]:
        nums = re.findall(r"_(\d+)(?:_|$)", name)
        value = max((int(n) for n in nums), default=0)
        return (value, -len(name))

    return sorted(candidates, key=rank, reverse=True)[0]


def build_fallbacks(workspace: Path) -> dict[str, dict[str, Path]]:
    """Map code -> local portrait thumbnail for bust-crop fallbacks."""
    data = workspace / "Portrait_showcase" / "data"
    result: dict[str, dict[str, Path]] = {"dolls": {}, "fairies": {}, "sangvis": {}}
    defaults = data / "manifests" / "defaults.json"
    if defaults.is_file():
        payload = json.loads(defaults.read_text(encoding="utf-8"))
        for item in payload.get("items", []):
            code = item.get("gunCode")
            thumb = item.get("thumb")
            if code and thumb and (data / thumb).is_file():
                result["dolls"].setdefault(code, data / thumb)
    sangvis = data / "sangvis.json"
    if sangvis.is_file():
        payload = json.loads(sangvis.read_text(encoding="utf-8"))
        for person in payload.get("persons", []):
            code = person.get("code")
            if not code:
                continue
            skins = person.get("skins", [])
            chosen = next((skin for skin in skins if skin.get("default")), None)
            if chosen is None:
                chosen = next((skin for skin in skins if skin.get("variant") == "5star"), None)
            if chosen is None and skins:
                chosen = skins[0]
            thumb = (chosen or {}).get("thumb")
            if thumb and (data / thumb).is_file():
                result["sangvis"].setdefault(code, data / thumb)
        for alias, base in SF_PORTRAIT_ALIASES.items():
            if base in result["sangvis"]:
                result["sangvis"].setdefault(alias, result["sangvis"][base])
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=ROOT.parent)
    parser.add_argument("--game-root", type=Path, default=None)
    parser.add_argument(
        "--only",
        action="append",
        choices=("dolls", "fairies", "sangvis"),
        help="Only rebuild one avatar category (can be repeated).",
    )
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    game_root = args.game_root
    if game_root is None:
        local_paths = workspace / "local_paths.json"
        if local_paths.is_file():
            game_root = Path(json.loads(local_paths.read_text(encoding="utf-8"))["gf1_game_root"])
        else:
            parser.error("--game-root is required when local_paths.json is absent")
    bundle_root = game_root / "GrilsFrontLine_Data" / "StreamingAssets" / "Res" / "Pc"
    if not bundle_root.is_dir():
        parser.error(f"bundle directory not found: {bundle_root}")

    import UnityPy

    head_bundle = find_bundle(bundle_root, "resourceiconspinehead.ab")
    fairy_bundle = find_bundle(bundle_root, "resourcefairy.ab")
    enemy_bundle = find_bundle(bundle_root, "resourceiconenemy.ab")
    if head_bundle is None or fairy_bundle is None:
        parser.error("head/fairy bundle not found")

    print("loading head bundle...", flush=True)
    heads = sprite_index(UnityPy.load(str(head_bundle)))
    print(f"head sprites: {len(heads)}", flush=True)
    print("loading fairy bundle...", flush=True)
    fairies_sprites = sprite_index(UnityPy.load(str(fairy_bundle)))
    print(f"fairy sprites: {len(fairies_sprites)}", flush=True)
    enemies = sprite_index(UnityPy.load(str(enemy_bundle))) if enemy_bundle else {}
    print(f"enemy sprites: {len(enemies)}", flush=True)

    codex_dir = ROOT / "app" / "data" / "codex"
    fallbacks = build_fallbacks(workspace)
    missing: dict[str, list[dict]] = {"dolls": [], "fairies": [], "sangvis": []}
    counts: dict[str, int] = {}

    def choose(kind: str, code: str) -> tuple[Image.Image | None, str]:
        if kind == "fairies":
            name = best_fairy(sorted(fairies_sprites), code)
            if name:
                image = render_sprite(fairies_sprites[name])
                if image:
                    return image, "icon"
            return None, "placeholder"
        if kind == "sangvis":
            # Correct identity first: the official SF portrait is much safer
            # than fuzzy-matching an enemy head icon (e.g. Guard -> Guard_chm
            # or Excutioner -> a mech sprite).
            portrait_code = SF_PORTRAIT_ALIASES.get(code, code)
            portrait = fallbacks.get("sangvis", {}).get(portrait_code) or fallbacks.get("sangvis", {}).get(code)
            if portrait:
                image = render_portrait(portrait)
                if image:
                    return image, "portrait"
            lookup_code = ALIASES.get(code, code)
            for pool in (enemies, heads):
                name = best_exact(sorted(pool), lookup_code)
                if name:
                    image = render_sprite(pool[name])
                    if image:
                        return image, "icon"
            return None, "placeholder"
        # dolls
        lookup_code = ALIASES.get(code, code)
        for pool in (heads,):
            name = best_head(sorted(pool), lookup_code)
            if name:
                image = render_sprite(pool[name])
                if image:
                    return image, "icon"
        portrait = fallbacks.get(kind, {}).get(code)
        if portrait:
            image = render_portrait(portrait)
            if image:
                return image, "portrait"
        return None, "placeholder"

    def emit(kind: str, rows: list[dict]) -> None:
        out_dir = ROOT / "assets" / "avatars" / kind
        out_dir.mkdir(parents=True, exist_ok=True)
        for row in rows:
            code = row["code"]
            image, source = choose(kind, code)
            if image is None:
                missing[kind].append(row)
                image = placeholder(row.get("name") or code, kind)
            image.save(out_dir / f"{slugify(code)}.webp", "WEBP", quality=88, method=6)
        counts[kind] = len(rows)
        print(f"{kind}: {len(rows)} avatars, missing {len(missing[kind])}", flush=True)

    dolls = json.loads((codex_dir / "dolls.json").read_text(encoding="utf-8"))
    fairies = json.loads((codex_dir / "fairies.json").read_text(encoding="utf-8"))
    sangvis = json.loads((codex_dir / "sangvis.json").read_text(encoding="utf-8"))
    selected = set(args.only or ("dolls", "fairies"))
    if "dolls" in selected:
        emit("dolls", dolls)
    if "fairies" in selected:
        emit("fairies", fairies)
    if "sangvis" in selected:
        emit("sangvis", sangvis)

    manifest = {
        "size": SIZE,
        "counts": counts,
        "missing": {
            kind: [{"code": row["code"], "name": row.get("name", "")} for row in rows]
            for kind, rows in missing.items()
        },
    }
    (ROOT / "assets" / "avatars" / "_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps({k: len(v) for k, v in missing.items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
