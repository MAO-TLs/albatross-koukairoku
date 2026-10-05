"use client";

import { useEffect } from "react";

export function InstallAnchorRelease() {
  useEffect(() => {
    let scrollFrame = 0;

    const scrollToInstall = () => {
      const target = document.getElementById("install");
      if (!target) return;

      window.history.replaceState(
        window.history.state,
        "",
        `${window.location.pathname}${window.location.search}`,
      );

      window.cancelAnimationFrame(scrollFrame);
      scrollFrame = window.requestAnimationFrame(() => {
        target.scrollIntoView({ behavior: "auto", block: "start" });
      });
    };

    const releaseInstallAnchor = () => {
      if (window.location.hash === "#install") scrollToInstall();
    };

    const handleInstallClick = (event: MouseEvent) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }

      const target = event.target;
      if (!(target instanceof Element)) return;
      if (!target.closest('a[href="#install"]')) return;

      event.preventDefault();
      scrollToInstall();
    };

    releaseInstallAnchor();
    window.addEventListener("hashchange", releaseInstallAnchor);
    document.addEventListener("click", handleInstallClick);

    return () => {
      window.cancelAnimationFrame(scrollFrame);
      window.removeEventListener("hashchange", releaseInstallAnchor);
      document.removeEventListener("click", handleInstallClick);
    };
  }, []);

  return null;
}
