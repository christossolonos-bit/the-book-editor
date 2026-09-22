"""
Export Prove Them Wrong as print-ready PDFs (5x8 Kindle + 6x9 Hardcopy).
Includes cover, chapter art, text, section breaks, and answer lines.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
)

from export_layout import chapter_pages

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "manuscript-export.json"
ART_DIR = ROOT / "public" / "art"
COVER = ROOT / "public" / "cover.png"
OUT_DIR = ROOT / "amazon-ready"

INK = HexColor("#1a1712")
MUTE = HexColor("#6e675c")
LINE = HexColor("#cfc4b3")
ACCENT = HexColor("#c45c26")

FORMATS = {
    "kindle": {
        "filename": "Prove Them Wrong - 5x8 Kindle.pdf",
        "pagesize": (5 * inch, 8 * inch),
        "margin": 0.55 * inch,
        "body": 11,
        "leading": 15,
        "title": 20,
        "chapter": 14,
        "indent": 14,
        "art_w": 3.4 * inch,
        "cover_w": 4.4 * inch,
        "answer_lines": 12,
        "art_max_h": 2.2 * inch,
    },
    "print": {
        "filename": "Prove Them Wrong - 6x9 Hardcopy.pdf",
        "pagesize": (6 * inch, 9 * inch),
        "margin": 0.7 * inch,
        "body": 12,
        "leading": 18,
        "title": 24,
        "chapter": 16,
        "indent": 18,
        "art_w": 4.0 * inch,
        "cover_w": 5.3 * inch,
        "answer_lines": 14,
        "art_max_h": 2.4 * inch,
    },
}

def esc(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def make_styles(fmt: dict):
    base = getSampleStyleSheet()
    styles = {
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=fmt["body"],
            leading=fmt["leading"],
            textColor=INK,
            alignment=TA_JUSTIFY,
            firstLineIndent=fmt["indent"],
            spaceAfter=2,
        ),
        "bodyFirst": ParagraphStyle(
            "BodyFirst",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=fmt["body"],
            leading=fmt["leading"],
            textColor=INK,
            alignment=TA_JUSTIFY,
            firstLineIndent=0,
            spaceAfter=2,
        ),
        "center": ParagraphStyle(
            "Center",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=fmt["body"],
            leading=fmt["leading"],
            textColor=INK,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceBefore=4,
            spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=fmt["body"],
            leading=fmt["leading"] + 2,
            textColor=INK,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceBefore=8,
            spaceAfter=10,
        ),
        "trythis": ParagraphStyle(
            "TryThis",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=fmt["body"],
            leading=fmt["leading"],
            textColor=INK,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceBefore=10,
            spaceAfter=8,
        ),
        "part": ParagraphStyle(
            "Part",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=9,
            leading=12,
            textColor=MUTE,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceAfter=6,
        ),
        "chapNum": ParagraphStyle(
            "ChapNum",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=13,
            textColor=MUTE,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceAfter=4,
        ),
        "chapTitle": ParagraphStyle(
            "ChapTitle",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=fmt["chapter"],
            leading=fmt["chapter"] + 4,
            textColor=INK,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceAfter=8,
        ),
        "ornament": ParagraphStyle(
            "Ornament",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=12,
            leading=14,
            textColor=MUTE,
            alignment=TA_CENTER,
            firstLineIndent=0,
            spaceAfter=14,
        ),
        "answerLabel": ParagraphStyle(
            "AnswerLabel",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=10,
            leading=12,
            textColor=MUTE,
            alignment=TA_LEFT,
            firstLineIndent=0,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            leading=10,
            textColor=MUTE,
            alignment=TA_CENTER,
        ),
    }
    return styles


def fit_image(path: Path, max_w: float, max_h: float | None = None) -> Image | None:
    if not path or not Path(path).exists():
        return None
    path = Path(path)
    with PILImage.open(path) as im:
        w, h = im.size
    aspect = h / float(w) if w else 1
    width = float(max_w)
    height = width * aspect
    if max_h is not None and height > float(max_h):
        height = float(max_h)
        width = height / aspect
    width *= 0.98
    height *= 0.98
    img = Image(str(path), width=width, height=height)
    img.hAlign = "CENTER"
    return img


class FittingArt(Flowable):
    """Chapter art that shrinks to the remaining space on the current page."""

    def __init__(self, path: Path, max_w: float, max_h: float):
        super().__init__()
        self.path = str(path)
        with PILImage.open(path) as im:
            w, h = im.size
        self.aspect = (h / float(w)) if w else 1.0
        self.max_w = float(max_w)
        self.max_h = float(max_h)
        self.drawWidth = self.max_w
        self.drawHeight = self.max_h
        self._avail_w = self.max_w

    def wrap(self, availWidth, availHeight):
        # Leave a little padding so ReportLab does not kick us to the next page
        usable_h = max(float(availHeight) - 8, 0.7 * inch)
        max_w = min(self.max_w, float(availWidth))
        max_h = min(self.max_h, usable_h)
        width = max_w
        height = width * self.aspect
        if height > max_h:
            height = max_h
            width = height / self.aspect if self.aspect else max_w
        self.drawWidth = width
        self.drawHeight = height
        self._avail_w = float(availWidth)
        return float(availWidth), height

    def draw(self):
        x = (self._avail_w - self.drawWidth) / 2.0
        self.canv.drawImage(
            self.path,
            x,
            0,
            width=self.drawWidth,
            height=self.drawHeight,
            preserveAspectRatio=True,
            mask="auto",
        )


def answer_lines(styles, count: int):
    bits = [Paragraph("YOUR ANSWER", styles["answerLabel"])]
    for _ in range(count):
        bits.append(Spacer(1, 10))
        bits.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=0, spaceAfter=0))
    return bits


def add_footer(canvas, doc):
    canvas.saveState()
    page_w, _ = doc.pagesize
    if doc.page > 1:
        canvas.setFont("Times-Roman", 8)
        canvas.setFillColor(MUTE)
        canvas.drawCentredString(page_w / 2, 0.35 * inch, str(doc.page - 1))
    canvas.restoreState()


def emit_block(story, block: dict, styles: dict, first_body: list):
    """Append one content block. first_body is a one-item list used as mutable flag."""
    text = block["text"]
    btype = block["type"]

    if btype == "section":
        story.append(Paragraph(esc(text), styles["section"]))
        if re.match(r"^Question\s+\d+", text, re.I):
            # Prompt may be on following body blocks; answer lines added by caller when page ends
            pass
        return

    if re.match(r"^Try this:", text, re.I):
        story.append(Paragraph(esc(text), styles["trythis"]))
        return

    if btype == "shout" or is_shout(text):
        story.append(Paragraph(esc(text), styles["center"]))
        return

    style = styles["bodyFirst"] if not first_body[0] else styles["body"]
    story.append(Paragraph(esc(text), style))
    first_body[0] = True


def is_shout(line: str) -> bool:
    t = line.strip()
    return bool(
        re.match(
            r"^(NO!|I WON'T|I WANT|I DON'T|I'LL SHOW|YEAH\.?|TAKE THAT|NOT TODAY|SHOW THEM|THEY WERE WRONG|HAVE A WONDERFUL LIFE\.?|YOU\.?|Prove them wrong\.?|Show them who you are\.?)$",
            t,
            re.I,
        )
        or (
            len(t) < 48
            and t == t.upper()
            and re.search(r"[A-Z]", t)
            and not re.search(r"[.!?]$", t)
        )
    )


def export_pdf(fmt_key: str, book: dict) -> Path:
    fmt = FORMATS[fmt_key]
    styles = make_styles(fmt)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / fmt["filename"]

    page_w, page_h = fmt["pagesize"]
    m = fmt["margin"]

    doc = BaseDocTemplate(
        str(out),
        pagesize=fmt["pagesize"],
        leftMargin=m,
        rightMargin=m,
        topMargin=m,
        bottomMargin=m + 0.1 * inch,
        title=book.get("title", "Proving Them Wrong"),
        author=book.get("author", "Christos Solonos"),
    )

    cover_frame = Frame(0, 0, page_w, page_h, id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    body_frame = Frame(m, m + 0.1 * inch, page_w - 2 * m, page_h - 2 * m - 0.1 * inch, id="normal")

    def cover_page(canvas, doc_):
        canvas.saveState()
        canvas.restoreState()

    def body_page(canvas, doc_):
        add_footer(canvas, doc_)

    doc.addPageTemplates(
        [
            PageTemplate(id="cover", frames=[cover_frame], onPage=cover_page),
            PageTemplate(id="main", frames=[body_frame], onPage=body_page),
        ]
    )

    story = build_story(book, fmt_key, fmt, styles)
    doc.build(story)
    return out


def build_story(book: dict, fmt_key: str, fmt: dict, styles: dict):
    story = []
    page_w, page_h = fmt["pagesize"]

    cover = fit_image(COVER, page_w, max_h=page_h)
    if cover:
        cover.drawWidth = page_w
        cover.drawHeight = page_h
        story.append(cover)
    else:
        story.append(Paragraph(esc(book["title"]), styles["chapTitle"]))
        story.append(Paragraph(esc(book["subtitle"]), styles["center"]))
        story.append(Paragraph(esc(book.get("author", "")), styles["center"]))

    story.append(NextPageTemplate("main"))
    story.append(PageBreak())

    last_part = None
    for ch in book["chapters"]:
        part = ch.get("part")
        if part and part != last_part and part not in ("Front", "Close"):
            story.append(Paragraph(esc(part.upper()), styles["part"]))
        last_part = part

        pages = chapter_pages(ch, fmt_key)
        first_body = [False]

        for page in pages:
            if not page["is_first"]:
                story.append(PageBreak())
                first_body[0] = False

            if page["is_first"]:
                if ch.get("number") is not None:
                    story.append(Paragraph(f"Chapter {ch['number']}", styles["chapNum"]))
                    story.append(Paragraph(esc(ch["title"]), styles["chapTitle"]))
                else:
                    story.append(Paragraph(esc(ch["title"]), styles["chapTitle"]))
                story.append(Paragraph("❦", styles["ornament"]))

            is_question_page = any(
                b["type"] == "section" and re.match(r"^Question\s+\d+", b["text"], re.I)
                for b in page["blocks"]
            )

            for block in page["blocks"]:
                emit_block(story, block, styles, first_body)

            if is_question_page:
                story.extend(answer_lines(styles, fmt["answer_lines"]))

            # Art at bottom of page — shrinks to leftover space so it does not jump alone
            if page["show_art"] and page["art_path"]:
                story.append(Spacer(1, 6))
                story.append(FittingArt(page["art_path"], fmt["art_w"], fmt["art_max_h"]))

        story.append(PageBreak())

    while story and isinstance(story[-1], PageBreak):
        story.pop()

    story.append(NextPageTemplate("cover"))
    story.append(PageBreak())
    back = ROOT / "public" / "back-cover.png"
    back_img = fit_image(back, page_w, max_h=page_h)
    if back_img:
        back_img.drawWidth = page_w
        back_img.drawHeight = page_h
        story.append(back_img)

    return story


def main():
    book = json.loads(JSON_PATH.read_text(encoding="utf8"))
    for key in ("print", "kindle"):
        path = export_pdf(key, book)
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"Saved: {path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
