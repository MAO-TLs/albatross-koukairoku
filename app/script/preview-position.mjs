export function previewPosition(rect, viewport, size) {
  const margin = 12, gap = 10;
  const width = Math.min(380, Math.max(0, viewport.width - margin * 2));
  const height = Math.min(size.height, 360, viewport.height * .58);
  const left = Math.min(Math.max(margin, rect.left), Math.max(margin, viewport.width - width - margin));
  const above = rect.top - gap - height;
  const top = above >= margin ? above : Math.min(rect.bottom + gap, Math.max(margin, viewport.height - height - margin));
  return { left, top: Math.max(margin, top), width, maxHeight: height };
}
