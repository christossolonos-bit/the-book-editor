/** Trim formats for Kindle vs hardcopy print. */

export const FORMATS = {
  kindle: {
    id: 'kindle',
    label: 'Kindle 5×8',
    shortLabel: '5″ × 8″',
    widthIn: 5,
    heightIn: 8,
    // Approximate content capacity for stable pages
    charsPerLine: 42,
    linesPerPage: 28,
    firstPageLineFactor: 0.68,
    artMaxLines: 10,
    questionLines: 12,
    margins: { top: 0.6, bottom: 0.6, left: 0.6, right: 0.5 },
  },
  print: {
    id: 'print',
    label: 'Hardcopy 6×9',
    shortLabel: '6″ × 9″',
    widthIn: 6,
    heightIn: 9,
    charsPerLine: 52,
    linesPerPage: 30,
    firstPageLineFactor: 0.68,
    artMaxLines: 11,
    questionLines: 15,
    margins: { top: 0.75, bottom: 0.75, left: 0.75, right: 0.65 },
  },
}
