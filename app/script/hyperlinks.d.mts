export type Hyperlink = { start: number; end: number; targetRef: string; preview?: string; alternatives?: { targetRef: string; preview?: string }[] };
export function validHyperlinks(text: string, links?: Hyperlink[], enabled?: boolean): Hyperlink[];
