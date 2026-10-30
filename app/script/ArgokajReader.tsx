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

function initialState() {
  const url = new URL(window.location.href);
  let hash = "";
  try { hash = decodeURIComponent(url.hash.slice(1)); } catch { /* Malformed link: leave no target. */ }
  return { script: url.searchParams.get("script") || "1001", scope: url.searchParams.get("scope") === "all" ? "all" : "script",
    q: url.searchParams.get("q") || "", errors: url.searchParams.get("errors") === "argokaj", hash };
}

export function ArgokajReader({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<Payload | null>(null);
  const [state, setState] = useState(initialState);
  const [failure, setFailure] = useState("");
  const [limit, setLimit] = useState(30);
  const query = useDeferredValue(state.q);
  useEffect(() => {
    const controller = new AbortController();
    fetch("../audit-data/comparison.json?rev=argokaj-audit-1", { signal: controller.signal, cache: "no-cache" })
      .then(r => { if (!r.ok) throw new Error("Could not load the Argokaj comparison."); return r.json(); })
      .then((payload: Payload) => {
        if (payload.schema !== "albatross-argokaj-reader/1" || payload.label !== "Argokaj" || payload.scripts.length !== 84 || payload.totalPassages !== 13128) throw new Error("The comparison data failed its integrity check.");
        setData(payload);
      }).catch(e => { if (e.name !== "AbortError") setFailure(String(e.message)); });
    return () => controller.abort();
  }, []);
  useEffect(() => { const sync = () => { setState(initialState()); setLimit(30); }; window.addEventListener("popstate",sync); return () => window.removeEventListener("popstate",sync); }, []);
  const script = data?.scripts.find(s => s.id === state.script) || data?.scripts[0];
  const groups = useMemo(() => {
    if (!data || !script) return [];
    const candidates = state.scope === "all" ? data.scripts.flatMap(s => s.groups) : script.groups;
    return candidates.filter(g => !query.trim() || g.source.some(s => matchesReaderText(s.japanese,query) || matchesReaderText(s.english,query) || matchesReaderText(s.speakerEn,query)) || g.target.some(t => matchesReaderText(t.text,query)));
  }, [data,script,state.scope,query]);
  const hashGroup = data?.refLocations[state.hash]?.group || state.hash;
  const anchorIndex = groups.findIndex(g => g.id === hashGroup);
  const visibleLimit = Math.max(limit, anchorIndex + 1);
  useEffect(() => {
    if (!data || !hashGroup) return;
    const timer = window.setTimeout(() => document.getElementById(hashGroup)?.scrollIntoView({block:"start"}), 50);
    return () => window.clearTimeout(timer);
  }, [data,hashGroup]);
  function change(patch: Partial<ReturnType<typeof initialState>>) {
    const next = { ...state, ...patch, hash: "" };
    setState(next); setLimit(30);
    const url = new URL(window.location.href);
    url.searchParams.set("compare","argokaj"); url.searchParams.set("script",next.script);
    const selected = data?.scripts.find(s => s.id === next.script);
    if (selected) url.searchParams.set("route",selected.routeId);
    next.errors ? url.searchParams.set("errors","argokaj") : url.searchParams.delete("errors");
    next.scope === "all" ? url.searchParams.set("scope","all") : url.searchParams.delete("scope");
    next.q ? url.searchParams.set("q",next.q) : url.searchParams.delete("q");
    url.hash = ""; window.history.replaceState(null,"",url);
  }
  const routes = [...new Map(data?.scripts.map(s => [s.routeId,s.routeLabel]) ?? []).entries()];
  return <div className="reader-shell shell argokaj-reader">
    <div className="reader-controls">
      <div className="control"><label htmlFor="arg-route">Section</label><select id="arg-route" value={script?.routeId || ""} disabled={!data} onChange={e => change({script: data!.scripts.find(s => s.routeId === e.target.value)!.id})}>{routes.map(([id,label]) => <option key={id} value={id}>{label}</option>)}</select></div>
      <div className="control"><label htmlFor="arg-script">Script</label><div className="script-picker">
        <button aria-label="Previous script" disabled={!data || !script || data.scripts.indexOf(script) === 0} onClick={() => change({script: data!.scripts[data!.scripts.indexOf(script!)-1].id})}>←</button>
        <select id="arg-script" value={script?.id || ""} disabled={!data} onChange={e => change({script:e.target.value})}>{data?.scripts.filter(s => s.routeId === script?.routeId).map(s => <option value={s.id} key={s.id}>{s.id}</option>)}</select>
        <button aria-label="Next script" disabled={!data || !script || data.scripts.indexOf(script) === data.scripts.length-1} onClick={() => change({script:data!.scripts[data!.scripts.indexOf(script!)+1].id})}>→</button>
      </div></div>
      <div className="control"><label htmlFor="arg-scope">Search scope</label><select id="arg-scope" value={state.scope} onChange={e => change({scope:e.target.value})}><option value="script">Current script</option><option value="all">All scripts</option></select></div>
      <div className="control"><label htmlFor="arg-search">Search English or 日本語</label><input id="arg-search" type="search" value={state.q} placeholder="Search…" onChange={e => change({q:e.target.value})} /></div>
      <span className="argokaj-result-count" aria-live="polite">{data ? `${groups.length.toLocaleString()} passage groups` : "Loading…"}</span>
      <div className="argokaj-toggles">
        <label><input type="checkbox" checked onChange={onClose} /> Display Argokaj for comparison</label>
        <label><input type="checkbox" checked={state.errors} onChange={e => change({errors:e.target.checked})} /> Display Argokaj errors</label>
        <a href="../audit/">Translation audit →</a>
      </div>
    </div>
    {failure ? <p role="alert" className="script-status">{failure}</p> : !data ? <p className="script-status">Loading comparison…</p> : <>
      <div className="script-meta"><h2>{state.scope === "all" ? "Corpus concordance" : `${script?.routeLabel} · Script ${script?.id}`}</h2><p>Japanese · MAO English · Argokaj</p></div>
      <p className="argokaj-alignment-note">Translations are grouped at shared script boundaries; paragraph breaks within a group need not correspond.</p>
      <div className="script-lines">{groups.slice(0,visibleLimit).map(g => <article className="script-line script-line-comparison" id={g.id} key={g.id}>
        <a className="line-ref" href={`?script=${g.scriptId}&compare=argokaj${state.errors ? "&errors=argokaj" : ""}#${encodeURIComponent(g.id)}`}>{state.scope === "all" ? `${g.scriptId} · ` : ""}{g.source[0]?.line}{g.source.length > 1 ? `–${g.source.at(-1)?.line}` : ""}</a>
        <div className="line-cell line-ja"><div className="line-cell-heading"><span className="edition-label">Japanese</span></div>{g.source.map(s => <p className="argokaj-paragraph" lang="ja" key={s.ref}>{s.japanese}</p>)}</div>
        <div className="line-cell line-en"><div className="line-cell-heading"><span className="edition-label">MAO English</span></div>{g.source.map(s => <div className="argokaj-paragraph" key={s.ref}>{s.speakerEn && <span className="speaker">{s.speakerEn}</span>}<p>{s.english}</p></div>)}</div>
        <div className="line-cell line-en line-argokaj"><div className="line-cell-heading"><span className="edition-label">Argokaj</span></div>{g.target.map(t => <p className="argokaj-paragraph" key={t.id}><PhraseText row={t} data={data} enabled={state.errors} /></p>)}</div>
      </article>)}</div>
      {!groups.length && <p className="script-empty">No matching passages.</p>}
      {visibleLimit < groups.length && <button className="concordance-more" onClick={() => setLimit(visibleLimit+30)}>Show more passage groups</button>}
    </>}
  </div>;
}
