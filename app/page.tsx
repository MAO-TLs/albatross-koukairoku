import { InstallAnchorRelease } from "./InstallAnchorRelease";
import { SiteNav } from "./SiteNav";
import { SiteFooter } from "./SiteFooter";
import stats from "../public/script-data/summary.json";
import patch from "../public/patch-release.json";

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
                English patch v{patch.version} <span aria-hidden="true">↓</span>
              </a>
            </div>
            <p className="compatibility">Script live · English patch v{patch.version}</p>
          </div>
          <div aria-hidden="true" />
        </div>
      </section>
      <section className="release-strip" aria-label="Release information">
        <div className="shell release-grid">
          <div><span className="release-label">Online script</span><strong>Live</strong></div>
          <div><span className="release-label">Script coverage</span><strong>Unabridged</strong></div>
          <div><span className="release-label">Passages</span><strong>{stats.totalLines.toLocaleString("en-US")}</strong></div>
          <div><span className="release-label">Patch</span><strong className="release-status">v{patch.version}</strong></div>
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
            <div className="section-heading"><p className="eyebrow">English patch</p><h2>Download v{patch.version}</h2></div>
            <p className="install-requirement">Requires your installed Japanese DVD retail copy
              (July 23, 2010) and Python 3. This is a patch, not the game.</p>
          </div>
          <div className="hero-actions">
            <a className="button button-primary" href={patch.downloadUrl}>Download English patch <span aria-hidden="true">↓</span></a>
            <a className="button button-secondary" href="./patch-installation.txt">Installation guide <span aria-hidden="true">→</span></a>
          </div>
          <p>Close the game, extract the ZIP to a separate folder, and run
            <em> Install English Patch.cmd</em> on Windows. Enter the installed game folder,
            not the DVD or disc-image folder. The installer checks the supported edition,
            preserves your saves, and backs up the original files.</p>
          <p>The complete English script and menus use IBM Plex Mono. Story text is
            horizontal and left-aligned, with word wrapping, intentional line breaks,
            and three reflowing sizes. The bundled font loads privately; no system-wide
            font installation is needed.</p>
          <p>Tested in Wine on macOS. Native Windows and a full-game playthrough have
            not been verified. No standalone Mac app is included.</p>
          <a className="text-link" href={patch.releaseUrl}>Release notes and checksums <span aria-hidden="true">→</span></a>
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
