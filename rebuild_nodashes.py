"""Refresh JSON from book.js and export Word without em dashes."""

import json
import subprocess
from pathlib import Path

import export_kindle_docx as ex

ROOT = Path(__file__).resolve().parent

NODE = r'''
import { bookMeta, chapters } from "./src/data/book.js";
import { writeFileSync } from "fs";
const payload = {
  ...bookMeta,
  chapters: chapters.map((c) => ({
    id: c.id,
    part: c.part,
    number: c.number,
    title: c.title,
    text: c.edited || c.original,
  })),
};
writeFileSync("manuscript-export.json", JSON.stringify(payload, null, 2), "utf8");
console.log("ok", payload.chapters.length);
'''


def main():
    subprocess.check_call(
        ["node", "--input-type=module", "-e", NODE],
        cwd=str(ROOT),
    )
    book = json.loads((ROOT / "manuscript-export.json").read_text(encoding="utf8"))
    blob = json.dumps(book)
    if "\u2014" in blob or "\u2013" in blob:
        raise SystemExit("Em/en dashes still present in export JSON")

    ex.JSON_PATH = ROOT / "manuscript-export.json"
    primary = ROOT / "Prove Them Wrong - 5x8 Kindle.docx"
    fallback = ROOT / "Prove Them Wrong - 5x8 Kindle (no dashes).docx"
    ex.OUT_PATH = primary
    try:
        ex.main()
    except PermissionError:
        ex.OUT_PATH = fallback
        ex.main()
        print("NOTE: original docx was open/locked; wrote fallback file instead.")


if __name__ == "__main__":
    main()
