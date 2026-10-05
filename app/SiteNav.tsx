type SiteNavProps = {
  releaseHref: string;
  scriptHref: string;
  currentPage: "release" | "script" | "none";
};

import { REPOSITORY_URL } from "../site-target.mjs";

export function SiteNav({
  releaseHref,
  scriptHref,
  currentPage,
}: SiteNavProps) {
  return (
    <nav className="nav shell" aria-label="Primary navigation">
      <a className="wordmark" href="https://mao-tls.github.io/">
        MAO Translations
      </a>
      <div className="nav-links">
        <a
          href={releaseHref}
          aria-current={currentPage === "release" ? "page" : undefined}
        >
          Release
        </a>
        <a
          href={scriptHref}
          aria-current={currentPage === "script" ? "page" : undefined}
        >
          Script
        </a>
        <a href={REPOSITORY_URL}>GitHub</a>
      </div>
    </nav>
  );
}
