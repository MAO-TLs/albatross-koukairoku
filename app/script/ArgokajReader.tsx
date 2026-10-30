"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { matchesReaderText } from "./reader-search.mjs";

type Finding = { id: string; ref: string; categories: string[]; severity: string; japanese: string; argokaj: string; explanation: string; surface: string; dossiers: string[] };
type Highlight = { start: number; end: number; findingId: string };
type Target = { id: string; text: string; highlights: Highlight[] };
type Source = { ref: string; readerRef: string; line: number; japanese: string; english: string; speakerEn: string };
type Group = { id: string; scriptId: string; source: Source[]; target: Target[] };
type Script = { id: string; routeId: string; routeLabel: string; lineCount: number; groups: Group[] };
type Payload = { schema: string; label: string; totalPassages: number; scripts: Script[]; findings: Record<string, Finding>; dossierLabels: Record<string,string>; refLocations: Record<string,{script:string;group:string}> };

function PhraseText({ row, data, enabled }: { row: Target; data: Payload; enabled: boolean }) {
  const [opened, setOpened] = useState<number | null>(null);
  const [dismissed, setDismissed] = useState(false);
  if (!enabled || !row.highlights.length) return <>{row.text}</>;
  const cuts = [...new Set([0, row.text.length, ...row.highlights.flatMap(h => [h.start, h.end])])].sort((a,b) => a-b);
  return <>{cuts.slice(0,-1).map((start, i) => {
    const end = cuts[i+1];
    const findings = [...new Set(row.highlights.filter(h => h.start < end && h.end > start).map(h => h.findingId))].map(id => data.findings[id]);
    const text = row.text.slice(start,end);
    if (!findings.length) return text;
    const tooltip = `note-${row.id}-${start}`;
    return <mark key={start} className={`argokaj-phrase${opened === start ? " is-open" : ""}${dismissed ? " is-dismissed" : ""}`} tabIndex={0} role="button"
      aria-label={`Error note: ${text}`} aria-describedby={tooltip} aria-expanded={opened === start}
      onMouseEnter={() => setDismissed(false)} onFocus={() => setDismissed(false)}
      onClick={() => { setDismissed(false); setOpened(opened === start ? null : start); }}
      onKeyDown={event => { if (event.key === "Escape") { setOpened(null); setDismissed(true); } if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setDismissed(false); setOpened(opened === start ? null : start); } }}>
      {text}
      <span className="argokaj-tooltip" id={tooltip} role="tooltip">
        {findings.map(f => <span className="argokaj-tooltip-note" key={f.id}>
          <strong>{f.categories.map(c => c.replaceAll("-"," ")).join(" · ")} · {f.severity}{f.surface === "translator_note" ? " · translator note" : ""}</strong>
          <span>{f.explanation}</span>
          <span lang="ja">{f.japanese}</span>
          <a href={`../audit/#dossier-${f.dossiers[0]}`}>Open audit dossier →</a>
        </span>)}
      </span>
    </mark>;
  })}</>;
}


type ViewOptions = { enabled: boolean; scriptId: string; scope: "script" | "corpus"; query: string; routeFilter: string };

export function useArgokajComparison({enabled, scriptId, scope, query, routeFilter}: ViewOptions) {
  const [data, setData] = useState<Payload | null>(null);
  const [failure, setFailure] = useState("");
  const deferredQuery = useDeferredValue(query);
  useEffect(() => {
    if (!enabled || data) return;
    const controller = new AbortController();
    fetch("../audit-data/comparison.json?rev=argokaj-audit-1", {signal: controller.signal, cache: "no-cache"})
      .then(r => { if (!r.ok) throw new Error("Could not load the Argokaj comparison."); return r.json(); })
      .then((payload: Payload) => {
        if (payload.schema !== "albatross-argokaj-reader/1" || payload.label !== "Argokaj" || payload.scripts.length !== 84 || payload.totalPassages !== 13128) throw new Error("The comparison data failed its integrity check.");
        setData(payload); setFailure("");
      }).catch(e => { if (e.name !== "AbortError") setFailure(String(e.message)); });
    return () => controller.abort();
  }, [enabled, data]);
  return useMemo(() => {
    const script = data?.scripts.find(s => s.id === scriptId);
    const candidates = scope === "corpus" ? data?.scripts.flatMap(s => s.groups) ?? [] : script?.groups ?? [];
    const matches = candidates.filter(g => !deferredQuery.trim() || matchesReaderText(g.scriptId,deferredQuery) ||
      g.source.some(s => [s.japanese,s.english,s.speakerEn,s.ref,s.readerRef].some(t => matchesReaderText(t,deferredQuery))) ||
      g.target.some(t => matchesReaderText(t.text,deferredQuery)));
    const scriptRoutes = new Map(data?.scripts.map(s => [s.id,s.routeId]));
    const groups = scope === "corpus" && routeFilter !== "all" ? matches.filter(g => scriptRoutes.get(g.scriptId) === routeFilter) : matches;
    const sourceCount = groups.reduce((sum,g) => sum+g.source.length,0);
    const errorGroups = scope === "script" ? script?.groups ?? [] : data?.scripts.flatMap(s => s.groups) ?? [];
    const errorCount = new Set(errorGroups.flatMap(g => g.target.flatMap(t => t.highlights.map(h => h.findingId)))).size;
    const routeCounts = new Map<string,number>();
    for (const g of matches) { const r=scriptRoutes.get(g.scriptId)!; routeCounts.set(r,(routeCounts.get(r)||0)+g.source.length); }
    const scriptCount = new Set(groups.map(g=>g.scriptId)).size;
    const sectionCount = new Set(groups.map(g=>scriptRoutes.get(g.scriptId))).size;
    const resultStatus = failure || (!data ? "Loading comparison…" :
      scope === "corpus" && !query.trim() ? "13,128 lines ready to search" :
      `${sourceCount.toLocaleString()} source lines in ${groups.length.toLocaleString()} ${query.trim() ? "matching " : ""}passage groups` +
      (scope === "corpus" ? ` across ${scriptCount} scripts and ${sectionCount} sections` : ""));
    return {data,failure,script,groups,matches,routeCounts,sourceCount,errorCount,resultStatus};
  }, [data,failure,scriptId,scope,deferredQuery,query,routeFilter]);
}

type View = ReturnType<typeof useArgokajComparison>;
export function ArgokajReader({view,scope,query,routeFilter,onRouteFilter,errors,pendingRef}: {
  view: View; scope: "script" | "corpus"; query: string; routeFilter: string;
  onRouteFilter: (route: string) => void; errors: boolean; pendingRef: string;
}) {
  const {data,failure,script,groups,matches,routeCounts,resultStatus} = view;
  const [limit,setLimit] = useState(40);
  useEffect(() => { setLimit(40); }, [script?.id,scope,query,routeFilter]);
  const anchor = groups.find(g => g.id === pendingRef || g.source.some(s => s.ref === pendingRef || s.readerRef === pendingRef))?.id;
  const visibleLimit = Math.max(limit,groups.findIndex(g=>g.id===anchor)+1);
  useEffect(() => {
    if (!anchor) return;
    const frame = requestAnimationFrame(() => {
      const target=document.getElementById(anchor);
      target?.scrollIntoView({block:"center"}); target?.focus({preventScroll:true});
    });
    return () => cancelAnimationFrame(frame);
  }, [anchor]);
  if (failure) return <p className="script-status" role="alert">{failure}</p>;
  if (!data) return <p className="script-status">Loading comparison…</p>;
  if (scope === "corpus" && !query.trim()) return <div className="concordance-prompt">
    <p className="eyebrow">Full-corpus search</p><h2>Search all 13,128 lines</h2>
    <p>Enter a Japanese or English phrase, speaker name, script number, or <code>albatross:</code> reference. Results include Argokaj and cover all 84 scripts.</p>
  </div>;
  const contextHref=(g:Group)=>`?route=${data.scripts.find(s=>s.id===g.scriptId)!.routeId}&script=${g.scriptId}&compare=argokaj${errors?"&errors=argokaj":""}#${encodeURIComponent(g.id)}`;
  const cells=(g:Group)=><>
    <div className="line-cell line-ja" lang="ja"><div className="line-cell-heading"><span className="edition-label" lang="en">Japanese</span></div>{g.source.map(s=><p className="argokaj-paragraph" key={s.ref}>{s.japanese.trim()}</p>)}</div>
    <div className="line-cell line-en"><div className="line-cell-heading"><span className="edition-label">MAO English</span></div>{g.source.map(s=><div className="argokaj-paragraph" key={s.ref}>{s.speakerEn&&<span className="speaker">{s.speakerEn}</span>}<p>{s.english}</p></div>)}</div>
    <div className="line-cell line-en line-todokanai"><div className="line-cell-heading"><span className="edition-label">Argokaj</span></div>{g.target.map(t=><p className="argokaj-paragraph" key={t.id}><PhraseText row={t} data={data} enabled={errors}/></p>)}</div>
  </>;
  const routes=[...new Map(data.scripts.map(s=>[s.routeId,s.routeLabel])).entries()];
  return <div className="argokaj-reader">
    <div className={`script-meta${scope==="corpus"?" concordance-meta":""}`}>
      <div>{scope==="corpus"&&<p className="eyebrow">All 84 scripts</p>}<h2>{scope==="corpus"?"Corpus concordance":`${script?.routeLabel} · ${script?.id}`}</h2></div>
      <p>{scope==="corpus"?resultStatus:`${script?.lineCount.toLocaleString()} source lines`}</p>
    </div>
    {scope==="corpus"&&<nav className="concordance-route-filter" aria-label="Filter concordance results by section">
      <button type="button" className={routeFilter==="all"?"is-active":""} aria-pressed={routeFilter==="all"} onClick={()=>onRouteFilter("all")}>All sections<span>{matches.reduce((n,g)=>n+g.source.length,0).toLocaleString()}</span></button>
      {routes.map(([id,label])=><button type="button" key={id} className={routeFilter===id?"is-active":""} aria-pressed={routeFilter===id} disabled={!routeCounts.get(id)} onClick={()=>onRouteFilter(id)}>{label}<span>{(routeCounts.get(id)||0).toLocaleString()}</span></button>)}
    </nav>}
    <p className="argokaj-alignment-note">Translations are grouped at shared script boundaries; paragraph breaks within a group need not correspond.</p>
    <div className={scope==="corpus"?"concordance-results":"script-lines"} id={scope==="corpus"?"concordance-results":"script-results"}>
      {groups.slice(0,visibleLimit).map(g=>scope==="corpus"?
        <article className="concordance-hit concordance-hit-comparison" id={g.id} key={g.id} tabIndex={-1}>
          <a className="concordance-hit-link" href={contextHref(g)}><span>{data.scripts.find(s=>s.id===g.scriptId)!.routeLabel} · Script {g.scriptId} · Lines {g.source[0]?.line}–{g.source.at(-1)?.line}</span><code>{g.source[0]?.readerRef}</code><strong>Open in script →</strong></a>
          <div className="concordance-hit-grid">{cells(g)}</div>
        </article>:
        <article className="script-line script-line-comparison" id={g.id} key={g.id} tabIndex={-1}>
          <a className="line-ref" href={contextHref(g)}>{g.source[0]?.line}{g.source.length>1?`–${g.source.at(-1)?.line}`:""}</a>{cells(g)}
        </article>)}
    </div>
    {!groups.length&&<p className="script-empty">No lines match this search.</p>}
    {visibleLimit<groups.length&&<button className="concordance-more" onClick={()=>setLimit(visibleLimit+40)}>Show more results</button>}
    <a className="back-to-controls" href="#reader-controls">Back to controls ↑</a>
  </div>;
}
