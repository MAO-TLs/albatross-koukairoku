export function safeHash(hash) {
  try { return decodeURIComponent(hash.replace(/^#/, "")); } catch { return ""; }
}
export function passageHref(targetRef) {
  const parts = targetRef.split(":");
  return `?route=${encodeURIComponent(parts[1])}&script=${encodeURIComponent(parts[2])}#${encodeURIComponent(targetRef).replaceAll("%3A", ":")}`;
}
export function parseReaderLocation(href, index) {
  const routes = index.routes.filter(route => route.id !== 'system');
  const url = new URL(href), p = url.searchParams;
  const normalize = v => v === "section-03c" ? "section-03" : v;
  let routeId = routes[0]?.id ?? "intro", scriptId = routes[0]?.scripts[0]?.id ?? "1001";
  const requested = p.get("script") === "s00_00" && p.get("route") === "section-00" ? "prologue" : normalize(p.get("route"));
  const route = routes.find(r => r.id === requested);
  if (route?.scripts.some(s => s.id === p.get("script"))) { routeId = route.id; scriptId = p.get("script"); }
  const ref = safeHash(url.hash).replace(/^albatross:section-00:s00_00:/, "albatross:prologue:s00_00:").replace(/^albatross:section-03c:/, "albatross:section-03:");
  const parts = ref.split(":"), target = routes.find(r => r.id === parts[1]);
  const valid = parts.length === 4 && parts[0] === "albatross" && target?.scripts.some(s => s.id === parts[2]);
  if (valid) { routeId = parts[1]; scriptId = parts[2]; }
  const filter = normalize(p.get("section") ?? p.get("chapter"));
  const comparison = Boolean(index.comparison) && p.get("compare") === "todokanai";
  return { routeId, scriptId, pendingRef: valid ? ref : "", searchScope: !valid && p.get("scope") === "all" ? "corpus" : "script", corpusQuery: p.get("q") ?? "", corpusRouteId: routes.some(r => r.id === filter) ? filter : "all", comparison, comparisonErrors: comparison && p.get("errors") === "todokanai" };
}
