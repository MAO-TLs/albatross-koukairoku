export function safeHash(hash: string): string;
export function passageHref(targetRef: string): string;
export function parseReaderLocation(href: string, index: { routes: { id: string; scripts: { id: string }[] }[]; comparison?: unknown }): {
  routeId: string; scriptId: string; pendingRef: string; searchScope: "corpus" | "script";
  scriptQuery: string; corpusQuery: string; corpusRouteId: string; comparison: boolean; comparisonErrors: boolean; argokaj: boolean; argokajErrors: boolean;
};
