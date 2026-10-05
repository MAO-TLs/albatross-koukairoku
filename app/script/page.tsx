import { SiteNav } from "../SiteNav";
import { SiteFooter } from "../SiteFooter";
import { ScriptBrowser } from "./ScriptBrowser";
import stats from "../../public/script-data/summary.json";

export default function ScriptPage() {
  return <main className="reader-page">
    <header className="reader-header">
      <SiteNav releaseHref="../" scriptHref="./" currentPage="script" />
      <div className="reader-intro shell"><p className="eyebrow">Complete script · {stats.totalLines.toLocaleString("en-US")} passages</p><h1>Script browser</h1><p>Read <em>Albatross Koukairoku</em> beside its Japanese source and search all {stats.totalScripts} scripts.</p></div>
    </header>
    <ScriptBrowser />
    <SiteFooter />
  </main>;
}
