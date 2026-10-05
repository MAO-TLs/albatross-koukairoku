import { InstallAnchorRelease } from "./InstallAnchorRelease";
import { SiteNav } from "./SiteNav";
import { SiteFooter } from "./SiteFooter";
import stats from "../public/script-data/summary.json";

export const dynamic = "force-static";

export default function Home() {
  return (
    <main>
      <InstallAnchorRelease />
      <section className="hero">
        <picture>
          <img className="hero-backdrop" src="./moonlit-sail-hero.png" alt="" aria-hidden="true" />
        </picture>
        <SiteNav releaseHref="./" scriptHref="./script/" currentPage="release" />
        <div className="hero-grid shell">
          <div className="hero-copy">
            <p className="eyebrow">An English translation by MAO</p>
            <h1>ALBATROSS<br />KOUKAIROKU</h1>
            <p className="dek">
              raiL-soft’s <em>Albatross Koukairoku</em>, now available to read in
              English. A complete translation preserving its notorious
              eccentricity, singular voice, and Mareni’s uncompromising prose.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="./script/">
                Read online <span aria-hidden="true">→</span>
              </a>
              <a className="button button-secondary" href="#install">
                Patch coming soon <span aria-hidden="true">↓</span>
              </a>
            </div>
            <p className="compatibility">Script live · Patch coming soon</p>
          </div>
          <div aria-hidden="true" />
        </div>
      </section>
      <section className="release-strip" aria-label="Release information">
        <div className="shell release-grid">
          <div><span className="release-label">Online script</span><strong>Live</strong></div>
          <div><span className="release-label">Script coverage</span><strong>Unabridged</strong></div>
          <div><span className="release-label">Passages</span><strong>{stats.totalLines.toLocaleString("en-US")}</strong></div>
          <div><span className="release-label">Patch</span><strong className="release-status">Coming soon</strong></div>
        </div>
      </section>
      <section className="section shell">
        <div className="section-heading">
          <p className="eyebrow">Read online</p>
          <h2>Browse the complete script</h2>
          <p>Read the Japanese and MAO English script side by side, with scene
            search, corpus search, and direct passage links. The unabridged
            bilingual script is available now.</p>
        </div>
        <a className="text-link" href="./script/">Open the script browser <span aria-hidden="true">→</span></a>
      </section>
      <section className="install-section" id="install">
        <div className="section shell">
          <div className="install-heading">
            <div className="section-heading"><p className="eyebrow">English patch</p><h2>Patch coming soon</h2></div>
            <p className="install-requirement">The complete bilingual script is live now. The English game patch,
              supported edition, and installation instructions will follow.</p>
          </div>
        </div>
      </section>
      <section className="section shell credits-section">
        <div className="section-heading"><p className="eyebrow">Credits</p><h2>MAO Translations</h2></div>
        <dl className="credits">
          <div><dt>Project Lead</dt><dd>MAO</dd></div>
          <div><dt>Translator</dt><dd>GPT-6 Astra</dd></div>
          <div><dt>Special Thanks</dt><dd>gambs</dd></div>
        </dl>
      </section>
      <SiteFooter />
    </main>
  );
}
