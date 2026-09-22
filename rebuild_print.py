"""Refresh manuscript JSON from book.js and export 6x9 hardcopy Word."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

NODE = r"""
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
console.log("ok", payload.author, payload.chapters.length);
"""


def main():
    subprocess.check_call(
        ["node", "--input-type=module", "-e", NODE],
        cwd=str(ROOT),
    )
    subprocess.check_call(["python", "export_print_docx.py"], cwd=str(ROOT))


if __name__ == "__main__":
    main()
