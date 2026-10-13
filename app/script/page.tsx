import { SiteNav } from "../SiteNav";
import { SiteFooter } from "../SiteFooter";
import { ScriptBrowser } from "./ScriptBrowser";
import stats from "../../public/script-data/summary.json";

export default function ScriptPage() {
  return <main className="reader-page">
    <header className="reader-header">
      <SiteNav releaseHref="../" scriptHref="./" currentPage="script" />
      <div className="reader-intro shell"><p className="eyebrow">Script version v1.0.0</p><h1>Script browser</h1><p>Read all {stats.totalLines.toLocaleString("en-US")} passages of <em>Albatross Koukairoku</em> beside their Japanese source and search all {stats.totalScripts} scripts.</p></div>
    </header>
    <ScriptBrowser />
    <SiteFooter />
  </main>;
}
