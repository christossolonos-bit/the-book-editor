"""
Shared manuscript layout helpers for PDF/Word exports.
Mirrors the editor: paginate by line budget, place art at the bottom of
pages that have spare room (chapter art on early pages, extras later).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ART_DIR = ROOT / "public" / "art"
EXTRA_ART = [ART_DIR / f"extra-{i:02d}.png" for i in range(1, 11)]

LAYOUT = {
    "kindle": {
        "chars_per_line": 42,
        "lines_per_page": 28,
        "first_page_factor": 0.68,
        "art_max_lines": 10,
        "header_lines": 8,
    },
    "print": {
        "chars_per_line": 52,
        "lines_per_page": 30,
        "first_page_factor": 0.68,
        "art_max_lines": 11,
        "header_lines": 8,
    },
}

SECTION_HEAD = re.compile(
    r"^(Question\s+\d+|Action step\.?$|Final words\.?$|Quick last note\.?$|Part\s+\d+\s*:)",
    re.I,
)
SHOUT = re.compile(
    r"^(NO!|I WON'T|I WANT|I DON'T|I'LL SHOW|YEAH\.?|TAKE THAT|NOT TODAY|SHOW THEM|"
    r"THEY WERE WRONG|HAVE A WONDERFUL LIFE\.?|YOU\.?|Prove them wrong\.?|"
    r"Show them who you are\.?)$",
    re.I,
)


def is_section_head(line: str) -> bool:
    return bool(SECTION_HEAD.match((line or "").strip()))


def is_shout(line: str) -> bool:
    t = (line or "").strip()
    if SHOUT.match(t):
        return True
    return bool(
        len(t) < 48
        and t == t.upper()
        and re.search(r"[A-Z]", t)
        and not re.search(r"[.!?]$", t)
    )


def hash_str(s: str) -> int:
    """Match StippleDraft.jsx hashStr (unsigned 32-bit)."""
    h = 0
    for ch in s:
        h = ((h * 31) + ord(ch)) & 0xFFFFFFFF
    return h


def pick_image(chapter_id: str, page_index: int, *, use_chapter_art: bool) -> Path | None:
    """Match editor intent: chapter art on first art page, extras afterward."""
    chapter_path = ART_DIR / f"{chapter_id}.png"
    if use_chapter_art and chapter_path.exists():
        return chapter_path
    existing = [p for p in EXTRA_ART if p.exists()]
    if not existing:
        return chapter_path if chapter_path.exists() else None
    idx = (hash_str(chapter_id) + page_index * 3) % len(existing)
    return existing[idx]


def estimate_lines(text: str, chars_per_line: int, block_type: str = "body") -> int:
    t = (text or "").strip()
    if not t:
        return 0
    base = max(1, (len(t) + chars_per_line - 1) // chars_per_line)
    if block_type in ("section", "shout"):
        return base + 1
    return base


def split_sentences(text: str) -> list[str]:
    parts = re.findall(r"[^.!?]+[.!?]+\s*|[^.!?]+$", text or "")
    return [p.strip() for p in parts if p.strip()]


def parse_blocks(text: str) -> list[dict]:
    """Mirror App.jsx parseBlocks for export."""
    if not (text or "").strip():
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = re.split(r"\n\n+", text)
    blocks: list[dict] = []

    for chunk in chunks:
        lines = [ln.strip() for ln in chunk.split("\n") if ln.strip()]
        if not lines:
            continue

        pending: list[str] = []

        def flush_pending():
            nonlocal pending
            if not pending:
                return
            all_short = len(pending) > 1 and all(len(ln) < 60 for ln in pending)
            if all_short:
                for ln in pending:
                    blocks.append(
                        {
                            "type": "shout" if is_shout(ln) else "body",
                            "text": ln,
                            "pageBreakBefore": False,
                        }
                    )
            else:
                joined = " ".join(pending)
                blocks.append(
                    {
                        "type": "shout" if is_shout(joined) else "body",
                        "text": joined,
                        "pageBreakBefore": False,
                    }
                )
            pending = []

        for line in lines:
            if is_section_head(line) and not re.match(r"^Try this:", line, re.I):
                flush_pending()
                blocks.append({"type": "section", "text": line, "pageBreakBefore": True})
            elif re.match(r"^Try this:", line, re.I):
                flush_pending()
                # Keep try-this with following lines in this chunk if any remain later
                pending.append(line)
            else:
                pending.append(line)
        flush_pending()

    # Attach following non-section body to Try this / Question prompts when
    # they were stored as bare section heads — body after section stays separate
    # which matches editor (section page gets prompt as next body block).
    return blocks


def paginate_blocks(blocks: list[dict], layout: dict) -> list[list[dict]]:
    """Mirror App.jsx paginateBlocks."""
    if not blocks:
        return [[]]

    chars = layout["chars_per_line"]
    lines_per_page = layout["lines_per_page"]
    pages: list[list[dict]] = []
    current: list[dict] = []
    used = 0
    budget = int(lines_per_page * layout["first_page_factor"])

    def push_page():
        nonlocal current, used, budget
        if not current:
            return
        pages.append(current)
        current = []
        used = 0
        budget = lines_per_page

    for block in blocks:
        if block.get("pageBreakBefore") and current:
            push_page()

        remaining = dict(block)
        while remaining:
            need = estimate_lines(remaining["text"], chars, remaining["type"])
            space = budget - used

            if current and need > space:
                if remaining["type"] == "body" and space >= 2:
                    sentences = split_sentences(remaining["text"])
                    fit_text = ""
                    rest: list[str] = []
                    filled = False
                    for i, sent in enumerate(sentences):
                        trial = f"{fit_text} {sent}".strip() if fit_text else sent
                        trial_lines = max(1, (len(trial) + chars - 1) // chars)
                        if trial_lines <= space:
                            fit_text = trial
                        else:
                            rest = sentences[i:]
                            filled = True
                            break
                    if fit_text and rest:
                        current.append({**remaining, "text": fit_text, "pageBreakBefore": False})
                        push_page()
                        remaining = {**remaining, "text": " ".join(rest), "pageBreakBefore": False}
                        continue
                    if fit_text and not filled:
                        current.append({**remaining, "text": fit_text, "pageBreakBefore": False})
                        remaining = None
                        break
                push_page()

            lines = estimate_lines(remaining["text"], chars, remaining["type"])
            if current and used + lines > budget:
                push_page()

            current.append(remaining)
            used += estimate_lines(remaining["text"], chars, remaining["type"])
            remaining = None

    if current:
        pages.append(current)
    return pages


def page_spare_lines(page_blocks: list[dict], page_index: int, layout: dict) -> int:
    chars = layout["chars_per_line"]
    page_lines = sum(estimate_lines(b["text"], chars, b["type"]) for b in page_blocks)
    header = layout["header_lines"] if page_index == 1 else 0
    return layout["lines_per_page"] - page_lines - header


def page_should_show_art(page_blocks: list[dict], page_index: int, layout: dict) -> bool:
    """Match App.jsx showDraftArt."""
    is_question = any(
        b["type"] == "section" and re.match(r"^Question\s+\d+", b["text"], re.I)
        for b in page_blocks
    )
    if is_question:
        return False
    return page_spare_lines(page_blocks, page_index, layout) >= layout["art_max_lines"]


def chapter_pages(chapter: dict, fmt_key: str) -> list[dict]:
    """
    Return list of {page_index, blocks, show_art, art_path, is_first, spare_lines}.
    Art sits at the bottom of pages with spare room (editor behavior).
    The first art-eligible page gets the chapter image; later ones get extras.
    """
    layout = LAYOUT[fmt_key]
    chapter_path = ART_DIR / f"{chapter['id']}.png"
    blocks = parse_blocks(chapter.get("text") or "")
    pages = paginate_blocks(blocks, layout)
    out = []
    used_chapter_art = False
    for i, page_blocks in enumerate(pages):
        page_index = i + 1
        spare = page_spare_lines(page_blocks, page_index, layout)
        show = page_should_show_art(page_blocks, page_index, layout)
        art = None
        if show:
            art = pick_image(
                chapter["id"],
                page_index,
                use_chapter_art=(not used_chapter_art),
            )
            if art and not used_chapter_art:
                used_chapter_art = True
        out.append(
            {
                "page_index": page_index,
                "blocks": page_blocks,
                "show_art": bool(show and art),
                "art_path": art,
                "is_first": i == 0,
                "spare_lines": spare,
            }
        )

    # Dense chapters: place chapter art on the page with the most spare room
    if chapter_path.exists() and out and not any(
        p["art_path"] and p["art_path"].resolve() == chapter_path.resolve() for p in out if p["show_art"]
    ):
        best = max(out, key=lambda p: p["spare_lines"])
        if best["spare_lines"] >= 6:
            best["show_art"] = True
            best["art_path"] = chapter_path

    return out
