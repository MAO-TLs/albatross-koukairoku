"use client";

import { createContext, useContext, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { previewPosition } from "./preview-position.mjs";
import { passageHref } from "./location.mjs";
import { scriptDataHref } from "./reader-data.mjs";
import "./hyperlink-preview.css";

type Language = "ja" | "en";
type PreviewLine = { ref: string; speakerJa: string; speakerEn: string; japanese: string; english: string; images?: {src: string; graphicId: number; embeddedJapaneseText?: boolean}[] };
type Entry = {targetRef: string; lines: PreviewLine[]};
type Active = {anchor: HTMLButtonElement; id: string; targetRef: string; language: Language; label: string; pinned: boolean};
type Controls = {active: Active | null; open: (next: Active, fromFocus?: boolean) => void; leave: () => void; keep: () => void; close: () => void; closeOwned: (id: string) => void; cardId: string};
const PreviewContext = createContext<Controls | null>(null);

export function HyperlinkPreviewProvider({children}: {children: ReactNode}) {
  const [active, setActive] = useState<Active | null>(null);
  const [entries, setEntries] = useState<Record<string, Entry> | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dismissedFocus = useRef<string | null>(null);
  const card = useRef<HTMLDivElement>(null);
  const cardId = useId();
  const [position, setPosition] = useState({left: 12, top: 12, width: 380, maxHeight: 360});
  const keep = () => { if (timer.current) clearTimeout(timer.current); };
  const close = () => { keep(); setActive(null); };
  const leave = () => {
    keep();
    timer.current = setTimeout(() => setActive(current => current?.pinned || current?.anchor === document.activeElement || card.current?.contains(document.activeElement) ? current : null), 180);
  };
  const closeOwned = (id: string) => setActive(current => current?.id === id ? null : current);
  const closeWithFocus = () => {
    if (!active) return;
    dismissedFocus.current = active.id;
    close();
    active.anchor.focus({preventScroll: true});
    dismissedFocus.current = null;
  };
  const open = (next: Active, fromFocus = false) => {
    keep();
    if (fromFocus && dismissedFocus.current === next.id) { dismissedFocus.current = null; return; }
    dismissedFocus.current = null;
    setActive(current => current?.id === next.id && current.pinned && !next.pinned ? current : next);
  };
  const requested = Boolean(active);

  useEffect(() => {
    if (!requested || entries) return;
    const controller = new AbortController();
    setError("");
    fetch(scriptDataHref("hyperlink-entries.json"), {signal: controller.signal})
      .then(response => { if (!response.ok) throw new Error("Could not load hyperlink preview."); return response.json(); })
      .then(data => { if (data.schema !== "albatross-hyperlink-previews/1") throw new Error("Unsupported hyperlink preview data."); setEntries(data.entries); })
      .catch(reason => { if (!controller.signal.aborted) setError(reason.message); });
    return () => controller.abort();
  }, [requested, entries, retry]);

  useEffect(() => {
    if (!active) return;
    const dismiss = (event: PointerEvent) => {
      if (!card.current?.contains(event.target as Node) && !active.anchor.contains(event.target as Node)) close();
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); closeWithFocus(); }
    };
    window.addEventListener("pointerdown", dismiss);
    window.addEventListener("keydown", escape);
    return () => { window.removeEventListener("pointerdown", dismiss); window.removeEventListener("keydown", escape); };
  }, [active]);

  useLayoutEffect(() => {
    if (!active) return;
    const place = () => {
      if (!active.anchor.isConnected) { close(); return; }
      const rect = active.anchor.getBoundingClientRect();
      setPosition(previewPosition(rect, {width: window.innerWidth, height: window.innerHeight}, {height: card.current?.scrollHeight ?? 360}));
    };
    place();
    const observer = new ResizeObserver(place);
    if (card.current) observer.observe(card.current);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => { observer.disconnect(); window.removeEventListener("resize", place); window.removeEventListener("scroll", place, true); };
  }, [active, entries, error]);

  useEffect(() => {
    const navigation = () => close();
    window.addEventListener("hashchange", navigation);
    window.addEventListener("popstate", navigation);
    return () => { keep(); window.removeEventListener("hashchange", navigation); window.removeEventListener("popstate", navigation); };
  }, []);

  const entry = active && entries?.[active.targetRef];
  const destinationHref = active ? passageHref(active.targetRef) : "#";
  return <PreviewContext.Provider value={{active, open, leave, keep, close, closeOwned, cardId}}>
    {children}
    {active && createPortal(<div ref={card} id={cardId} role="dialog" aria-modal="false" aria-label={active.label} lang={active.language} className="hyperlink-preview" style={position}
      onMouseEnter={keep} onMouseLeave={leave} onFocus={keep}
      onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget as Node) && event.relatedTarget !== active.anchor) leave(); }}>
      <div className="hyperlink-preview-heading"><strong>{active.label}</strong><button type="button" aria-label={active.language === "ja" ? "閉じる" : "Close preview"} onClick={closeWithFocus}>×</button></div>
      {!entries && !error && <p role="status">{active.language === "ja" ? "読み込み中…" : "Loading…"}</p>}
      {error && <p role="status">{error} <button type="button" onClick={() => setRetry(value => value + 1)}>Retry</button></p>}
      {entries && !entry && <p>{active.language === "ja" ? "プレビューは利用できません。" : "Preview unavailable. Open the passage below."}</p>}
      {entry?.lines.map(line => <div className="hyperlink-preview-passage" key={line.ref}>
        {(active.language === "ja" ? line.speakerJa : line.speakerEn) && !line.images?.length && <strong>{active.language === "ja" ? line.speakerJa : line.speakerEn}</strong>}
        {!line.images?.length && <p>{active.language === "ja" ? line.japanese : line.english}</p>}
        {line.images?.map(image => <figure key={image.src}><img src={`..${image.src}`} alt={active.language === "ja" ? `ゲーム画像 ${image.graphicId}` : `Source game image ${image.graphicId}`} /></figure>)}
      </div>)}
      <a className="hyperlink-preview-open" href={destinationHref} onClick={close}>{active.language === "ja" ? "本文を開く →" : "Open passage →"}</a>
    </div>, document.body)}
  </PreviewContext.Provider>;
}

export function HyperlinkTrigger({targetRef, language, label, children}: {targetRef: string; language: Language; label: string; children: ReactNode}) {
  const controls = useContext(PreviewContext);
  const id = useId();
  const button = useRef<HTMLButtonElement>(null);
  const expanded = controls?.active?.id === id;
  const latestControls = useRef(controls);
  latestControls.current = controls;
  useEffect(() => () => latestControls.current?.closeOwned(id), [id]);
  if (!controls) return <a href={`#${encodeURIComponent(targetRef)}`}>{children}</a>;
  const show = (pinned = false, fromFocus = false) => { if (button.current) controls.open({anchor: button.current, id, targetRef, language, label, pinned}, fromFocus); };
  return <button ref={button} type="button" className="hyperlink-trigger" aria-haspopup="dialog" aria-expanded={expanded} aria-controls={expanded ? controls.cardId : undefined}
    onMouseEnter={() => show()} onMouseLeave={controls.leave} onFocus={() => show(false, true)}
    onBlur={event => { if (!(event.relatedTarget as HTMLElement)?.closest(".hyperlink-preview")) controls.leave(); }}
    onClick={() => expanded && controls.active?.pinned ? controls.close() : show(true)}>{children}</button>;
}
