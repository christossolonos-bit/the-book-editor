/**
 * Page art: generated images only (no SVG drawings).
 * Chapter openers use chapter art; later pages use unique extras.
 */

const CHAPTER_IMAGES = {
  prologue: '/art/prologue.png',
  ch01: '/art/ch01.png',
  ch02: '/art/ch02.png',
  ch03: '/art/ch03.png',
  ch04: '/art/ch04.png',
  ch05: '/art/ch05.png',
  ch06: '/art/ch06.png',
  ch07: '/art/ch07.png',
  ch08: '/art/ch08.png',
  ch09: '/art/ch09.png',
  ch10: '/art/ch10.png',
  ch11: '/art/ch11.png',
  ch12: '/art/ch12.png',
  ch13: '/art/ch13.png',
  closing: '/art/closing.png',
}

const EXTRA_IMAGES = [
  '/art/extra-01.png',
  '/art/extra-02.png',
  '/art/extra-03.png',
  '/art/extra-04.png',
  '/art/extra-05.png',
  '/art/extra-06.png',
  '/art/extra-07.png',
  '/art/extra-08.png',
  '/art/extra-09.png',
  '/art/extra-10.png',
]

function hashStr(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h
}

function pickImage(chapterId, pageIndex) {
  const chapterImage = CHAPTER_IMAGES[chapterId]

  // First art page of a chapter: dedicated chapter image
  if (pageIndex <= 1 && chapterImage) return chapterImage

  // Later pages: rotate through extras so pages differ and never use drawings
  const idx = (hashStr(chapterId) + pageIndex * 3) % EXTRA_IMAGES.length
  return EXTRA_IMAGES[idx]
}

export default function StippleDraft({ chapterId, pageIndex = 1 }) {
  const src = pickImage(chapterId, pageIndex)

  return (
    <figure className="stipple-draft stipple-draft--photo">
      <img className="page-art-image" src={src} alt="" draggable={false} />
    </figure>
  )
}
