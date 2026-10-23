// Shared reader-search contract. Keep distributed copies identical.
// Latin/other spaced-language words match at word edges; Japanese can match
// within unspaced text. Apostrophes/hyphens delimit names (Dora's, Dora-chan).
const japanese = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/u;
const word = /[\p{L}\p{M}\p{N}_]/u;
const wordChar = char => Boolean(char) && word.test(char) && !japanese.test(char);
export const normalizeReaderSearch = value => String(value ?? '').normalize('NFKC').toLowerCase().replace(/\s+/gu, ' ').trim();

function positions(text, query, firstOnly = false) {
  const found = [];
  const left = wordChar(Array.from(query)[0]);
  const right = wordChar(Array.from(query).at(-1));
  for (let start = text.indexOf(query); start >= 0; start = text.indexOf(query, start + 1)) {
    const end = start + query.length;
    const before = start ? String.fromCodePoint(text.codePointAt(start - (/[\uDC00-\uDFFF]/u.test(text[start - 1]) ? 2 : 1))) : '';
    const after = end < text.length ? String.fromCodePoint(text.codePointAt(end)) : '';
    if ((!left || !wordChar(before)) && (!right || !wordChar(after))) {
      found.push({start, end});
      if (firstOnly) break;
    }
  }
  return found;
}

export function matchesReaderText(value, query) {
  const needle = normalizeReaderSearch(query);
  if (!needle) return true;
  const text = normalizeReaderSearch(value);
  if (positions(text, needle, true).length) return true;
  return japanese.test(needle) && positions(text.replace(/\s/gu, ''), needle.replace(/\s/gu, ''), true).length > 0;
}

// Original UTF-16 offsets, even after width/ligature/combining-mark folding.
export function readerMatchRanges(value, query) {
  const needle = normalizeReaderSearch(query);
  if (!needle) return [];
  const chars = [], starts = [], ends = [];
  for (const part of String(value).matchAll(/\P{M}\p{M}*|\p{M}+/gu)) {
    const normalized = part[0].normalize('NFKC').toLowerCase();
    for (let i = 0; i < normalized.length; i++) {
      const c = /\s/u.test(normalized[i]) ? ' ' : normalized[i];
      if (c === ' ' && chars.at(-1) === ' ') { ends[ends.length - 1] = part.index + part[0].length; continue; }
      chars.push(c); starts.push(part.index); ends.push(part.index + part[0].length);
    }
  }
  let ranges = positions(chars.join(''), needle).map(r => ({start: starts[r.start], end: ends[r.end - 1]}));
  if (japanese.test(needle)) {
    const kept = chars.map((c, i) => ({c, i})).filter(x => x.c !== ' ');
    ranges.push(...positions(kept.map(x => x.c).join(''), needle.replace(/\s/gu, '')).map(r => ({start: starts[kept[r.start].i], end: ends[kept[r.end - 1].i]})));
  }
  const merged = [];
  for (const range of ranges.sort((a,b) => a.start - b.start || a.end - b.end)) {
    const previous = merged.at(-1);
    if (previous && range.start <= previous.end) previous.end = Math.max(previous.end, range.end);
    else merged.push(range);
  }
  return merged;
}
