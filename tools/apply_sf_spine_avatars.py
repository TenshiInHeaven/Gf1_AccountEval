import base64
import json
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(r"E:\python\gf_forge\account_evaluate")
TMP = Path(r"E:\python\gf_forge\Tmp")
OUT = ROOT / "assets" / "avatars" / "sangvis"
OUT.mkdir(parents=True, exist_ok=True)

results = {}
for name in ("sf_spine_one.json", "sf_spine_region.json"):
    path = TMP / name
    if not path.is_file():
        continue
    payload = json.loads(path.read_text(encoding="utf-8"))
    results.update(payload.get("results", {}))

print("rendered", len(results), sorted(results))
for code, data_url in sorted(results.items()):
    encoded = data_url.split(",", 1)[1]
    image = Image.open(BytesIO(base64.b64decode(encoded))).convert("RGBA")
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    image = ImageOps.contain(image, (156, 156), Image.LANCZOS)
    canvas = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((160 - image.width) // 2, (160 - image.height) // 2))
    canvas.save(OUT / f"{code}.webp", "WEBP", quality=92, method=6)

missing = sorted(
    item["code"]
    for item in json.loads((ROOT / "app/data/codex/sangvis.json").read_text(encoding="utf-8"))
    if item["code"] not in results
)
print("fallback portraits", len(missing), missing)
