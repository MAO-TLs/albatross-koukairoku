import type { Metadata } from "next";
import audit from "../../public/audit-data/dossiers.json";
import { SiteNav } from "../SiteNav";
import { SiteFooter } from "../SiteFooter";
import { DossierAnchors } from "./DossierAnchors";

export const dynamic = "force-static";
export const metadata: Metadata = {
  title: "Albatross Koukairoku · Argokaj Translation Audit",
  description: "A source-based audit of Argokaj's Albatross Koukairoku translation.",
};

function contextHref(context: {script: string; group: string}) {
  return `../script/?script=${context.script}&compare=argokaj&errors=argokaj#${encodeURIComponent(context.group)}`;
}

export default function AuditPage() {
  const rendered = new Set<string>();
  return <main className="reader-page audit-page">
    <DossierAnchors />
    <header className="reader-header">
      <SiteNav releaseHref="../" scriptHref="../script/" currentPage="audit" />
      <div className="reader-intro audit-intro shell">
        <p className="eyebrow">Source-based editorial audit</p>
        <h1>Argokaj translation audit</h1>
        <p>Findings checked against the Japanese DVD script and its surrounding context. The dossiers collect recurring problems, with examples, counterexamples, and limits on each claim.</p>
      </div>
    </header>
    <div className="audit-shell shell">
      <section className="audit-summary" aria-labelledby="audit-summary-title">
        <div className="audit-summary-heading"><div><p className="eyebrow">Completed corpus reading</p><h2 id="audit-summary-title">What the audit records</h2></div><p>84 scripts · 13,128 source passages reviewed</p></div>
        <div className="audit-stat-grid">
          <div><strong>{audit.summary.uniqueRetainedFindings.toLocaleString()}</strong><span>Total errors</span></div>
          <div><strong>{audit.summary.uniqueSeverity.material.toLocaleString()}</strong><span>Material errors</span></div>
          <div><strong>{audit.summary.uniqueSeverity.minor.toLocaleString()}</strong><span>Minor errors</span></div>
        </div>
        <p className="audit-method-note">Both material and minor errors count toward the total. These labels distinguish severity, not whether a finding is an error.</p>
        <p className="audit-method-note">{audit.reviewNote}</p>
        <p className="audit-method-note">{audit.countingNote} Rejected and unresolved claims are excluded from the reader highlights. The ledger includes 8 translator-note findings, identified separately in their explanations.</p>
        <p className="audit-method-note">{audit.scopeNote}</p>
      </section>
      <section className="audit-dossiers" aria-labelledby="audit-dossiers-title">
        <header className="audit-dossiers-heading"><p className="eyebrow">Work-wide dossiers</p><h2 id="audit-dossiers-title">Recurring patterns</h2>
          <p className="audit-method-note">Category totals cover the retained ledger; the cited passages below are selected examples. Character and world dossiers use explicitly selected memberships. Counts overlap and must not be added together.</p>
          <p className="audit-dossiers-evidence-count">{audit.dossierCount} dossiers · {audit.citedPassageCount} example cards · {audit.uniqueCitedFindingCount} distinct cited findings · {audit.selectedCounterexampleCount} distinct counterexamples</p>
        </header>
        <div className="audit-group-list">{audit.groups.map(group => <details className="audit-group" key={group.id} open>
          <summary><span>{group.label}</span><small>{group.dossiers.length} dossier{group.dossiers.length === 1 ? "" : "s"}</small></summary>
          <div className="audit-dossier-list">{group.dossiers.map(dossier => <details className="audit-dossier" id={`dossier-${dossier.id}`} key={dossier.id}>
            <summary><div><p className="audit-dossier-count">{dossier.retainedCount.toLocaleString()} errors · {dossier.exampleCount} cited examples · {dossier.counterexampleCount} counterexample{dossier.counterexampleCount === 1 ? "" : "s"}</p><h3>{dossier.title}</h3></div><span className="audit-dossier-toggle"><span>Open dossier</span><span>Close dossier</span></span></summary>
            <div className="audit-dossier-body">
              <a className="audit-permalink" href={`#dossier-${dossier.id}`}>Permanent link #</a>
              <p className="audit-dossier-claim">{dossier.claim}</p>
              <dl className="audit-dossier-definition"><div><dt>Japanese pattern</dt><dd>{dossier.sourcePattern}</dd></div><div><dt>Argokaj effect</dt><dd>{dossier.comparatorEffect}</dd></div><div><dt>Limits</dt><dd>{dossier.limits}</dd></div></dl>
              <p className="audit-dossier-diagnostic"><b>Corpus diagnostic</b>{dossier.diagnostic} {"evidenceFloorException" in dossier ? String(dossier.evidenceFloorException) : ""}</p>
              <div className="audit-example-list">
                {dossier.examples.map(example => {
                  const id = rendered.has(example.findingId) ? undefined : example.findingId;
                  rendered.add(example.findingId);
                  return <a className="audit-example audit-example-finding" href={contextHref(example.context)} id={id} key={example.findingId}>
                    <div className="audit-example-heading"><span>{example.severity} error{example.surface === "translator_note" ? " · translator note" : ""}</span><code>{example.ref}</code></div>
                    <p lang="ja">{example.japanese}</p><p>{example.argokaj}</p><small>{example.note}</small><b>Open in script context →</b>
                  </a>;
                })}
                {dossier.counterexamples.map(example => <a className="audit-example audit-example-counterexample" href={contextHref(example.context)} key={example.id}>
                  <div className="audit-example-heading"><span>Counterexample</span><code>{example.ref}</code></div>
                  <p lang="ja">{example.japanese}</p><p>{example.argokaj}</p><small>{example.whyItWorksOrLimitsClaim}</small><b>Open in script context →</b>
                </a>)}
              </div>
            </div>
          </details>)}</div>
        </details>)}</div>
      </section>
    </div>
    <SiteFooter />
  </main>;
}
