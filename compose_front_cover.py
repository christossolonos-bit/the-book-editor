"""Compose a powerful front cover: big title, safe margins from edges."""

from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ART = Path(r"d:\final book editor\public\cover-art.png")
SRC_FALLBACK = Path(
    r"C:\Users\User\.cursor\projects\d-final-book-editor\assets\prove-them-wrong-cover-art.png"
)
OUT = Path(r"d:\final book editor\public\cover.png")


def load_art() -> Image.Image:
    src = ART if ART.exists() else SRC_FALLBACK
    im = Image.open(src).convert("RGBA")
    return im.resize((1200, 1800), Image.Resampling.LANCZOS)


def main():
    im = load_art()
    w, h = im.size

    rgb = im.convert("RGB")
    rgb = ImageEnhance.Contrast(rgb).enhance(1.08)
    rgb = ImageEnhance.Color(rgb).enhance(1.06)
    im = rgb.convert("RGBA")

    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for i, a in enumerate(range(160, 0, -7)):
        sd.rectangle([0, 0, w, int(h * 0.04) + i * 4], fill=(6, 8, 12, min(a, 170)))
    for i, a in enumerate(range(130, 0, -8)):
        sd.rectangle([0, h - int(h * 0.05) - i * 4, w, h], fill=(6, 8, 12, min(a, 150)))
    base = Image.alpha_composite(im, shade)
    draw = ImageDraw.Draw(base)

    arial_black = r"C:\Windows\Fonts\ariblk.ttf"
    arial_bold = r"C:\Windows\Fonts\arialbd.ttf"
    georgia = r"C:\Windows\Fonts\georgia.ttf"
    title_font_path = arial_black if Path(arial_black).exists() else arial_bold

    mx = int(w * 0.07)
    top_y = int(h * 0.08)
    author_y = int(h * 0.88)
    max_text_w = w - 2 * mx

    def fit_font(text: str, start: int, min_size: int = 64) -> ImageFont.FreeTypeFont:
        size = start
        while size >= min_size:
            font = ImageFont.truetype(title_font_path, size)
            bbox = draw.textbbox((0, 0), text, font=font)
            if bbox[2] - bbox[0] <= max_text_w:
                return font
            size -= 2
        return ImageFont.truetype(title_font_path, min_size)

    def center_text(text, font, y, fill=(255, 255, 255, 255), stroke=4):
        """Draw centered text; return y just below the ink (incl. stroke)."""
        probe = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
        tw = probe[2] - probe[0]
        x = (w - tw) // 2 - probe[0]
        draw.text((x + 4, y + 5), text, font=font, fill=(0, 0, 0, 150), stroke_width=stroke)
        draw.text(
            (x, y),
            text,
            font=font,
            fill=fill,
            stroke_width=stroke,
            stroke_fill=(0, 0, 0, 210),
        )
        ink = draw.textbbox((x, y), text, font=font, stroke_width=stroke)
        return ink[3]

    y = top_y
    font1 = fit_font("PROVING THEM", 128, min_size=88)
    y = center_text("PROVING THEM", font1, y, stroke=6) + 8
    font2 = fit_font("WRONG", 250, min_size=140)
    y = center_text("WRONG", font2, y, stroke=8) + 28

    # Soft dark band behind subtitle only (below title)
    sub_lines = textwrap.wrap(
        "A Life Beyond Fear, Epilepsy, and Other People's Limits", width=34
    )
    font_sub = ImageFont.truetype(georgia, 38)
    sub_h = 0
    for line in sub_lines:
        bb = draw.textbbox((0, 0), line, font=font_sub, stroke_width=2)
        sub_h += (bb[3] - bb[1]) + 10

    band = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bd.rectangle(
        [mx - 16, y - 10, w - mx + 16, y + sub_h + 14],
        fill=(8, 10, 14, 110),
    )
    base = Image.alpha_composite(base, band)
    draw = ImageDraw.Draw(base)

    for line in sub_lines:
        y = center_text(line, font_sub, y, fill=(250, 245, 235, 255), stroke=2) + 10

    font_author = ImageFont.truetype(arial_bold, 38)
    center_text("CHRISTOS SOLONOS", font_author, author_y, stroke=2)

    out = base.convert("RGB")
    out.save(OUT, "PNG", optimize=True)
    print(f"saved {OUT} {out.size}")
    print(f"margins side={mx/w:.0%} top={top_y/h:.0%} author_y={author_y/h:.0%}")


if __name__ == "__main__":
    main()
