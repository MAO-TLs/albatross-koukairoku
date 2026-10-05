// Offsets are UTF-16 string indices, matching the reader's other spans.
export function validHyperlinks(text, links = [], enabled = true) {
  if (!enabled) return [];
  let cursor = 0;
  return [...links].filter(link => link && typeof link === 'object')
    .sort((a, b) => a.start - b.start).filter(link => {
      const valid = Number.isInteger(link.start) && Number.isInteger(link.end)
        && link.start >= cursor && link.end > link.start && link.end <= text.length
        && typeof link.targetRef === 'string' && link.targetRef.length > 0
        && !splitsSurrogate(text, link.start) && !splitsSurrogate(text, link.end);
      if (valid) cursor = link.end;
      return valid;
    });
}
function splitsSurrogate(text, offset) {
  return offset > 0 && offset < text.length
    && /[\uD800-\uDBFF]/.test(text[offset - 1])
    && /[\uDC00-\uDFFF]/.test(text[offset]);
}
