const segmenter = new Intl.Segmenter('ru', { granularity: 'grapheme' });

export const splitGraphemes = (value: string) =>
  Array.from(segmenter.segment(value), ({ segment }) => segment);

function lastGlyphPoint(text: Node | null, end?: number) {
  if (!(text instanceof globalThis.Text)) return undefined;
  const visible = text.data.slice(0, end ?? text.length).trimEnd();
  const glyph = segmenter.segment(visible).containing(visible.length - 1);
  if (!glyph) return undefined;

  const range = document.createRange();
  range.setStart(text, glyph.index);
  range.setEnd(text, glyph.index + glyph.segment.length);
  const box = range.getBoundingClientRect();
  return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
}

export function answerGazePoint(element: HTMLElement) {
  return lastGlyphPoint(element.firstChild);
}

const mirrorStyles = [
  'font-family',
  'font-size',
  'font-weight',
  'font-style',
  'line-height',
  'letter-spacing',
  'word-spacing',
  'padding-top',
  'padding-right',
  'padding-bottom',
  'padding-left',
  'direction',
  'word-break',
  'tab-size',
];

export function draftGazePoint(field: HTMLTextAreaElement, mirror: HTMLDivElement, caret: number) {
  const styles = getComputedStyle(field);
  for (const property of mirrorStyles) {
    mirror.style.setProperty(property, styles.getPropertyValue(property));
  }
  mirror.style.width = `${field.clientWidth}px`;
  mirror.textContent = field.value;
  const point = lastGlyphPoint(mirror.firstChild, caret);
  if (!point) return undefined;

  const input = field.getBoundingClientRect();
  const copy = mirror.getBoundingClientRect();
  const x = input.left + field.clientLeft + point.x - copy.left - field.scrollLeft;
  const y = input.top + field.clientTop + point.y - copy.top - field.scrollTop;
  return {
    x: Math.max(input.left, Math.min(input.right, x)),
    y: Math.max(input.top, Math.min(input.bottom, y)),
  };
}
