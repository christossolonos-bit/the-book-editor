# Proving Them Wrong — Book Editor

Local React (Vite) editor for Christos Solonos’s memoir *Proving Them Wrong*.

## Run the editor

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

Open http://127.0.0.1:5174/

## Export for Amazon (local only)

```bash
node --input-type=module -e "import { bookMeta, chapters } from './src/data/book.js'; import { writeFileSync } from 'fs'; writeFileSync('manuscript-export.json', JSON.stringify({...bookMeta, chapters: chapters.map(c => ({id:c.id,part:c.part,number:c.number,title:c.title,text:c.edited||c.original}))}, null, 2))"
python export_pdf.py
python export_google_docs.py
```

Outputs land in `amazon-ready/` (ignored by git — regenerate when needed).

## Stack

- React + Vite
- Chapter art in `public/art/`
- PDF/Word export scripts in the project root
