import { useMemo, useState } from 'react'
import { bookMeta, chapters as initialChapters } from './data/book'
import { FORMATS } from './formats'
import StippleDraft from './components/StippleDraft'
import './App.css'

function countWords(text) {
  if (!text?.trim()) return 0
  return text.trim().split(/\s+/).length
}

function StatusBadge({ status }) {
  const labels = {
    pending: 'Pending',
    in_progress: 'In progress',
    edited: 'Edited',
  }
  return <span className={`badge ${status}`}>{labels[status] || status}</span>
}

function groupByPart(list) {
  const parts = []
  for (const chapter of list) {
    const last = parts[parts.length - 1]
    if (!last || last.name !== chapter.part) {
      parts.push({ name: chapter.part, items: [chapter] })
    } else {
      last.items.push(chapter)
    }
  }
  return parts
}

function parseBlocks(text) {
  if (!text?.trim()) return []
  const chunks = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split(/\n\n+/)
  const blocks = []

  for (const chunk of chunks) {
    const lines = chunk
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean)
    if (!lines.length) continue

    const pending = []
    const flushPending = () => {
      if (!pending.length) return
      const allShort = pending.length > 1 && pending.every((l) => l.length < 60)
      if (allShort) {
        for (const line of pending) blocks.push(makeBlock(line))
      } else {
        blocks.push(makeBlock(pending.join(' ')))
      }
      pending.length = 0
    }

    for (const line of lines) {
      if (/^Question\s+\d+/i.test(line)) {
        flushPending()
        blocks.push({ type: 'section', text: line, pageBreakBefore: true })
      } else if (/^Action step\.?$/i.test(line)) {
        flushPending()
        blocks.push({ type: 'section', text: line, pageBreakBefore: true })
      } else if (/^Part\s+\d+\s*:/i.test(line)) {
        flushPending()
        blocks.push({ type: 'section', text: line, pageBreakBefore: true })
      } else if (/^(Final words|Quick last note)\.?$/i.test(line)) {
        flushPending()
        blocks.push({ type: 'section', text: line, pageBreakBefore: true })
      } else {
        pending.push(line)
      }
    }
    flushPending()
  }
  return blocks
}

function makeBlock(text) {
  return { type: lineLengthType(text), text, pageBreakBefore: false }
}

function lineLengthType(text) {
  const t = text.trim()
  if (
    /^(NO!|I WON'T|I WANT|I DON'T|I'LL SHOW|YEAH\.?|TAKE THAT|NOT TODAY|SHOW THEM|THEY WERE WRONG|HAVE A WONDERFUL LIFE\.?|YOU\.?)$/i.test(
      t,
    )
  ) {
    return 'shout'
  }
  if (t.length < 48 && !/[.!?]$/.test(t) && t === t.toUpperCase() && /[A-Z]/.test(t)) {
    return 'shout'
  }
  if (/^Question\s+\d+/i.test(t)) return 'section'
  if (/^Part\s+\d+\s*:/i.test(t)) return 'section'
  if (
    /^(Meditation|Limit testing|Awareness|Affirmations on paper|People as fuel|The Filter Rule|Don't argue\. Outperform\.|Action step|Final checklist|Your new starting line|Final words|Quick last note|The three types of naysayers|The Fearful|The Projectors|The Controllers|Fix your environment|How to test your limits without breaking|Find people with the same drive\.|Drop the dead weight\.|Build your proof stack\.|Try this:.*)$/i.test(
      t,
    )
  ) {
    return 'section'
  }
  if (t.length < 36 && /^[A-Z][^.!?]*:$/.test(t) && t.split(' ').length <= 5) {
    return 'section'
  }
  return 'body'
}

function estimateLines(block, charsPerLine) {
  const len = Math.max(block.text.length, 1)
  if (block.type === 'section') return 2
  if (block.type === 'shout') return 1.4
  return Math.max(1, Math.ceil(len / charsPerLine))
}

function splitSentences(text) {
  const parts = text.match(/[^.!?]+[.!?]+\s*|[^.!?]+$/g)
  return (parts || [text]).map((s) => s.trim()).filter(Boolean)
}

/** Stable pagination: fill fixed line budgets; split long paragraphs on sentences. */
function paginateBlocks(blocks, format) {
  if (!blocks.length) return [[]]

  const { charsPerLine, linesPerPage, firstPageLineFactor } = format
  const pages = []
  let current = []
  let used = 0
  let budget = Math.floor(linesPerPage * firstPageLineFactor)

  const pushPage = () => {
    if (!current.length) return
    pages.push(current)
    current = []
    used = 0
    budget = linesPerPage
  }

  for (const block of blocks) {
    if (block.pageBreakBefore && current.length) pushPage()

    let remaining = { ...block }
    while (remaining) {
      const need = estimateLines(remaining, charsPerLine)
      const space = budget - used

      if (current.length && need > space) {
        // Try to split body paragraph to fill the page cleanly
        if (remaining.type === 'body' && space >= 2) {
          const sentences = splitSentences(remaining.text)
          let fitText = ''
          let restSentences = []
          let filled = false

          for (let i = 0; i < sentences.length; i++) {
            const trial = fitText ? `${fitText} ${sentences[i]}` : sentences[i]
            const trialLines = Math.ceil(trial.length / charsPerLine)
            if (trialLines <= space) {
              fitText = trial
            } else {
              restSentences = sentences.slice(i)
              filled = true
              break
            }
          }

          if (fitText && restSentences.length) {
            current.push({ ...remaining, text: fitText, pageBreakBefore: false })
            pushPage()
            remaining = { ...remaining, text: restSentences.join(' '), pageBreakBefore: false }
            continue
          }

          if (fitText && !filled) {
            current.push({ ...remaining, text: fitText, pageBreakBefore: false })
            remaining = null
            break
          }
        }

        pushPage()
      }

      const lines = estimateLines(remaining, charsPerLine)
      if (current.length && used + lines > budget) {
        pushPage()
      }

      current.push(remaining)
      used += estimateLines(remaining, charsPerLine)
      remaining = null
    }
  }

  if (current.length) pages.push(current)
  return pages
}

function BookParagraph({ block, isFirstBody }) {
  const useDropCap =
    isFirstBody &&
    block.type === 'body' &&
    block.text.trim().length > 55 &&
    !/^\s*What is the next step/i.test(block.text)

  const className = [
    'book-p',
    `book-p--${block.type}`,
    useDropCap ? 'book-p--first' : '',
    !useDropCap && isFirstBody ? 'book-p--lead' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return <p className={className}>{block.text}</p>
}

function BookPage({
  pageIndex,
  totalPages,
  chapter,
  blocks,
  isFirstPage,
  showTitlePage,
  showBackCover,
  book,
  format,
}) {
  let sawBody = false
  const isQuestionPage = blocks.some(
    (b) => b.type === 'section' && /^Question\s+\d+/i.test(b.text),
  )
  const lineCount = isQuestionPage ? format.questionLines : 0
  const pageLines = blocks.reduce((n, b) => n + estimateLines(b, format.charsPerLine), 0)
  const spareLines = format.linesPerPage - pageLines - (isFirstPage ? 8 : 0)
  const showDraftArt =
    !showTitlePage && !showBackCover && !isQuestionPage && spareLines >= format.artMaxLines

  return (
    <article
      className={`book-page book-page--${format.id}${
        showTitlePage || showBackCover ? ' book-page--title' : ''
      }${showBackCover ? ' book-page--back' : ''}${
        isQuestionPage ? ' book-page--question' : ''
      }${showDraftArt ? ' book-page--art' : ''}`}
      style={{
        width: `${format.widthIn}in`,
        height: `${format.heightIn}in`,
      }}
    >
      <div className="book-page-inner">
        {showTitlePage ? (
          <div className="title-page title-page--cover">
            <img
              className="cover-image"
              src="/cover.png"
              alt={`${book.title} — front cover`}
            />
          </div>
        ) : showBackCover ? (
          <div className="title-page title-page--cover">
            <img
              className="cover-image"
              src="/back-cover.png"
              alt={`${book.title} — back cover`}
            />
          </div>
        ) : (
          <>
            {isFirstPage && (
              <header className="chapter-open">
                {chapter.part && chapter.part !== 'Front' && chapter.part !== 'Close' ? (
                  <p className="chapter-open-part">{chapter.part}</p>
                ) : null}
                {chapter.number != null ? (
                  <p className="chapter-open-number">Chapter {chapter.number}</p>
                ) : null}
                <h2 className="chapter-open-title">{chapter.title}</h2>
                <div className="chapter-open-ornament" aria-hidden="true">
                  ❦
                </div>
              </header>
            )}

            <div className="book-body">
              {blocks.map((block, i) => {
                const isBody = block.type === 'body'
                const isFirstBody = isBody && !sawBody && isFirstPage
                if (isBody) sawBody = true
                return (
                  <BookParagraph
                    key={`${pageIndex}-${i}`}
                    block={block}
                    isFirstBody={isFirstBody}
                  />
                )
              })}
            </div>

            {isQuestionPage ? (
              <div className="answer-lines" aria-label="Space for your answer">
                <p className="answer-lines-label">Your answer</p>
                {Array.from({ length: lineCount }, (_, i) => (
                  <div key={i} className="answer-line" />
                ))}
              </div>
            ) : null}

            {showDraftArt ? (
              <div className="chapter-draft-slot">
                <StippleDraft chapterId={chapter.id} pageIndex={pageIndex} />
              </div>
            ) : null}
          </>
        )}
      </div>
      {!showTitlePage && !showBackCover && (
        <footer className="book-page-footer">
          <span className="book-running">{book.title}</span>
          <span className="book-folio">{pageIndex}</span>
        </footer>
      )}
      <div className="book-page-meta">
        {format.shortLabel}
        {showBackCover
          ? ' · back cover'
          : totalPages > 1
            ? ` · page ${pageIndex} of ${totalPages}`
            : ''}
      </div>
    </article>
  )
}

export default function App() {
  const [chapters, setChapters] = useState(initialChapters)
  const [activeId, setActiveId] = useState(initialChapters[0].id)
  const [view, setView] = useState('book')
  const [editMode, setEditMode] = useState(false)
  const [formatId, setFormatId] = useState('print')

  const format = FORMATS[formatId]
  const active = chapters.find((c) => c.id === activeId) || chapters[0]
  const parts = useMemo(() => groupByPart(chapters), [chapters])

  const editedCount = chapters.filter((c) => c.status === 'edited').length
  const progress = Math.round((editedCount / chapters.length) * 100)

  const displayText = active.edited || active.original || ''
  const pages = useMemo(() => {
    const blocks = parseBlocks(displayText)
    return paginateBlocks(blocks, format)
  }, [displayText, format])

  function updateEdited(value) {
    setChapters((prev) =>
      prev.map((c) => {
        if (c.id !== activeId) return c
        const trimmed = value.trim()
        let status = c.status
        if (!trimmed) status = 'pending'
        else if (trimmed === (c.original || '').trim()) status = 'in_progress'
        else status = 'edited'
        return { ...c, edited: value, status }
      }),
    )
  }

  const label =
    active.number != null ? `Chapter ${active.number}: ${active.title}` : active.title

  return (
    <div className="app" data-format={format.id}>
      <aside className="sidebar">
        <div className="brand">
          <p className="brand-kicker">{format.label}</p>
          <h1>{bookMeta.title}</h1>
          <p>{bookMeta.subtitle}</p>
        </div>

        <div className="progress-wrap">
          <div className="format-toggle" role="tablist" aria-label="Book format">
            <button
              type="button"
              className={formatId === 'kindle' ? 'active' : ''}
              onClick={() => setFormatId('kindle')}
            >
              Kindle 5×8
            </button>
            <button
              type="button"
              className={formatId === 'print' ? 'active' : ''}
              onClick={() => setFormatId('print')}
            >
              Hardcopy 6×9
            </button>
          </div>
          <div className="progress-label" style={{ marginTop: '0.75rem' }}>
            <span>Chapters ready</span>
            <span>
              {editedCount}/{chapters.length} · {progress}%
            </span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <nav className="chapter-nav" aria-label="Chapters">
          {parts.map((part) => (
            <div key={part.name}>
              <p className="part-label">{part.name}</p>
              {part.items.map((chapter) => {
                const title =
                  chapter.number != null
                    ? `${chapter.number}. ${chapter.title}`
                    : chapter.title
                return (
                  <button
                    key={chapter.id}
                    type="button"
                    className={`chapter-btn${chapter.id === activeId ? ' active' : ''}`}
                    onClick={() => {
                      setActiveId(chapter.id)
                      setEditMode(false)
                    }}
                  >
                    <div className="chapter-btn-top">
                      <span className="chapter-title">{title}</span>
                      <StatusBadge status={chapter.status} />
                    </div>
                    <span className="chapter-meta">{chapter.note}</span>
                  </button>
                )
              })}
            </div>
          ))}
        </nav>
      </aside>

      <main className="main">
        <header className="toolbar">
          <div className="toolbar-left">
            <h2>{label}</h2>
            <p>
              {format.label} · fixed pages · {countWords(displayText)} words · {pages.length}{' '}
              page{pages.length === 1 ? '' : 's'}
            </p>
          </div>

          <div className="toolbar-actions">
            <div className="view-toggle" role="tablist" aria-label="View mode">
              <button
                type="button"
                className={view === 'book' ? 'active' : ''}
                onClick={() => {
                  setView('book')
                  setEditMode(false)
                }}
              >
                Book pages
              </button>
              <button
                type="button"
                className={view === 'original' ? 'active' : ''}
                onClick={() => setView('original')}
              >
                Original
              </button>
              <button
                type="button"
                className={view === 'compare' ? 'active' : ''}
                onClick={() => setView('compare')}
              >
                Compare
              </button>
            </div>
            <button type="button" className="btn-accent" onClick={() => setEditMode((v) => !v)}>
              {editMode ? 'Close editor' : 'Edit text'}
            </button>
          </div>
        </header>

        <div className="editor-body">
          {view === 'book' && (
            <div className="book-stage">
              {activeId === 'prologue' && (
                <BookPage
                  pageIndex={0}
                  totalPages={pages.length}
                  chapter={active}
                  blocks={[]}
                  isFirstPage={false}
                  showTitlePage
                  showBackCover={false}
                  book={bookMeta}
                  format={format}
                />
              )}

              {pages.map((pageBlocks, i) => (
                <BookPage
                  key={`${activeId}-${format.id}-page-${i}`}
                  pageIndex={i + 1}
                  totalPages={pages.length}
                  chapter={active}
                  blocks={pageBlocks}
                  isFirstPage={i === 0}
                  showTitlePage={false}
                  showBackCover={false}
                  book={bookMeta}
                  format={format}
                />
              ))}

              {activeId === 'closing' && (
                <BookPage
                  pageIndex={pages.length + 1}
                  totalPages={pages.length}
                  chapter={active}
                  blocks={[]}
                  isFirstPage={false}
                  showTitlePage={false}
                  showBackCover
                  book={bookMeta}
                  format={format}
                />
              )}
            </div>
          )}

          {view === 'original' && (
            <div className="book-stage">
              <article
                className={`book-page book-page--${format.id} book-page--draft`}
                style={{ width: `${format.widthIn}in`, height: 'auto', minHeight: `${format.heightIn}in` }}
              >
                <div className="book-page-inner">
                  <header className="chapter-open">
                    <p className="chapter-open-number">Original draft</p>
                    <h2 className="chapter-open-title">{active.title}</h2>
                  </header>
                  <div className="book-body">
                    {parseBlocks(active.original).map((block, i) => (
                      <BookParagraph
                        key={i}
                        block={block}
                        isFirstBody={i === 0 && block.type === 'body'}
                      />
                    ))}
                  </div>
                </div>
              </article>
            </div>
          )}

          {view === 'compare' && (
            <div className="compare-stage">
              <div className="compare-col">
                <h3 className="compare-label">Original</h3>
                <article className="book-page book-page--compact">
                  <div className="book-page-inner">
                    {parseBlocks(active.original).map((block, i) => (
                      <BookParagraph
                        key={i}
                        block={block}
                        isFirstBody={i === 0 && block.type === 'body'}
                      />
                    ))}
                  </div>
                </article>
              </div>
              <div className="compare-col">
                <h3 className="compare-label">Edited</h3>
                <article className="book-page book-page--compact">
                  <div className="book-page-inner">
                    {parseBlocks(active.edited || '').length ? (
                      parseBlocks(active.edited).map((block, i) => (
                        <BookParagraph
                          key={i}
                          block={block}
                          isFirstBody={i === 0 && block.type === 'body'}
                        />
                      ))
                    ) : (
                      <p className="book-p book-p--empty">No edited text yet.</p>
                    )}
                  </div>
                </article>
              </div>
            </div>
          )}

          {editMode && (
            <section className="raw-edit" aria-label="Raw text editor">
              <div className="pane-header">
                <h3>Raw chapter text</h3>
                <span className="word-count">{countWords(active.edited || '')} words</span>
              </div>
              <textarea
                className="edit-area"
                value={active.edited ?? ''}
                onChange={(e) => updateEdited(e.target.value)}
                placeholder="Edit the chapter text here…"
              />
            </section>
          )}
        </div>
      </main>
    </div>
  )
}
