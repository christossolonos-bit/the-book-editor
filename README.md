# Hey. I’m your book editor.

Not a blank template. Not another “AI writing assistant” that polishes your sentences into someone else’s voice.

I’m the workspace built for **Proving Them Wrong** — Christos Solonos’s memoir about epilepsy, fear, other people’s limits, and the stubborn decision to keep going anyway.

I was made so you can *see* the book as a book: real pages, real trim sizes, chapter art where it belongs, questions with room to answer. Kindle **5×8**. Hardcopy **6×9**. Flip through. Fix the flow. Feel whether a chapter *lands*.

---

## What I do for you

- **Hold the manuscript** — prologue through closing, reshaped into chapters that breathe  
- **Show print-ready pages** — fixed size, no endless scroll pretending to be a book  
- **Place the art** — chapter images and extras at the bottom of pages with room, not dumped mid-paragraph  
- **Export when you’re ready** — local PDF and Word for Amazon, so *you* publish first  

I don’t upload your story. I stay on your machine until you say otherwise.

---

## Start me up

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

Then open **http://127.0.0.1:5174/** and meet the pages.

> Tip: if something else is already on port 5173, I’m happy on **5174**.

---

## When the draft is ready to leave the nest

Refresh the export JSON, then build the files Amazon wants:

```bash
node --input-type=module -e "import { bookMeta, chapters } from './src/data/book.js'; import { writeFileSync } from 'fs'; writeFileSync('manuscript-export.json', JSON.stringify({...bookMeta, chapters: chapters.map(c => ({id:c.id,part:c.part,number:c.number,title:c.title,text:c.edited||c.original}))}, null, 2))"
python export_pdf.py
python export_google_docs.py
```

You’ll find fresh files in `amazon-ready/`. Those big PDFs stay local on purpose — regenerate them whenever the text or covers change.

Cover need a punch? Run `python compose_front_cover.py` and I’ll rebuild the front with title that actually *shows up*.

---

## What’s under the hood

React + Vite. Manuscript in `src/data/book.js`. Art in `public/art/`. Export scripts at the project root. Simple tools for a hard story.

---

## One last thing

This book was never meant to sit in a messy draft forever.  
I’m here so the pages are clear, the voice stays yours, and the reader gets the fire — not the fog.

**Prove them wrong.**  
I’ll keep the layout honest while you do.
