from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((8, 8, SIZE - 8, SIZE - 8), radius=52, fill=(15, 20, 28, 255), outline=(242, 193, 78, 255), width=3)
# subtle inner frame
d.rounded_rectangle((22, 22, SIZE - 22, SIZE - 22), radius=40, outline=(242, 193, 78, 70), width=2)
font = None
for candidate in ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/arialbd.ttf"):
    try:
        font = ImageFont.truetype(candidate, 90)
        break
    except Exception:
        pass
text = "GF"
if font:
    box = d.textbbox((0, 0), text, font=font)
    d.text(((SIZE - (box[2] - box[0])) / 2, (SIZE - (box[3] - box[1])) / 2 - 12), text, font=font, fill=(242, 193, 78, 255))
small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
label = "ACCOUNT FORGE"
box = d.textbbox((0, 0), label, font=small)
d.text(((SIZE - (box[2] - box[0])) / 2, 190), label, font=small, fill=(133, 146, 166, 255))
img.save(Path(__file__).resolve().parents[1] / "assets" / "app_icon.png")
print("ok")
