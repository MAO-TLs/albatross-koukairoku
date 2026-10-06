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
              raiL-soft’s <em>Albatross Koukairoku</em>, now available in
              English. A complete translation preserving its notorious
              eccentricity, singular voice, and Mareni’s uncompromising prose.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href={patch.downloadUrl}>
                Download complete release <span aria-hidden="true">↓</span>
              </a>
              <a className="button button-secondary" href="./script/">
                Script <span aria-hidden="true">→</span>
              </a>
            </div>
            <p className="compatibility">
              {(patch.size / 1_000_000).toFixed(1)} MB · <a href={patch.releaseUrl}>Release notes</a>
              {" · Version "}{patch.version}{" · Windows + Wine · Japanese DVD retail edition required"}
            </p>
          </div>
          <div aria-hidden="true" />
        </div>
      </section>
      <section className="release-strip" aria-label="Release information">
        <div className="shell release-grid">
          <div><span className="release-label">Version</span><strong>v{patch.version}</strong></div>
          <div><span className="release-label">Script coverage</span><strong>Main game</strong></div>
          <div><span className="release-label">Passages</span><strong>{stats.totalLines.toLocaleString("en-US")} passages</strong></div>
          <div><span className="release-label">Status</span><strong className="release-status">Released</strong></div>
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
            <div className="section-heading"><p className="eyebrow">Installation</p><h2>How to install the patch</h2></div>
            <p className="install-requirement">Requires your own legally obtained Japanese
              <em> Albatross Koukairoku</em> DVD retail installation (July 23, 2010)
              and Python 3. Other editions are not supported.</p>
          </div>
          <ol className="install-steps">
            <li><span>01</span><div>
              <h3>Back up the originals</h3>
              <p>Keep a backup of your unmodified Japanese installation and saves,
                and close the game before applying the patch.</p>
            </div></li>
            <li><span>02</span><div>
              <h3>Apply the English patch</h3>
              <p>Extract the ZIP to a separate folder. On Windows, run{" "}
                <code>Install English Patch.cmd</code> and enter the installed game
                folder—not the DVD or disc-image folder. On macOS with Wine, use
                the Python installer as directed in the <a href="./patch-installation.txt">bundled README</a>.
                The installer checks the edition, preserves saves and keeps the
                original files in <code>MAO-original-backup</code>.</p>
            </div></li>
            <li><span>03</span><div>
              <h3>Start the game</h3>
              <p>Launch <code>Albatross.exe</code> and begin a new English game.
                IBM Plex Mono loads from the bundled font without a system-wide
                installation. Story text wraps and reflows at all three sizes,
                preserving intentional line breaks.</p>
            </div></li>
          </ol>
          <aside className="install-warning">
            <strong>Platform validation</strong>
            <p>The opening, settings, save/load, font loading and reported truncation
              regression were checked in Wine on macOS. Native Windows and a full-game
              playthrough have not been verified. No standalone Mac app is included.</p>
          </aside>
          <aside className="install-warning">
            <strong>Translation patch</strong>
            <p>Already on v1.0.0? The October 7 hotfix corrects the Stop Voice
              labels and fixes a system-code-page-dependent story-text crash.
              Re-download and rerun the installer, keeping
              <code>MAO-original-backup</code> in place. Your saves are preserved.</p>
            <p>This unofficial, noncommercial patch does not include the original
              game. Japanese saves may cache old text/layout state. See the
              <a href="./patch-installation.txt"> installation guide</a> for restoration
              instructions and the <a href={patch.releaseUrl}>release notes</a> for checksums.</p>
          </aside>
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
