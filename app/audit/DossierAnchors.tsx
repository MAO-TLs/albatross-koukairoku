"use client";
import { useEffect } from "react";

export function DossierAnchors() {
  useEffect(() => {
    function reveal() {
      let id = "";
      try { id = decodeURIComponent(window.location.hash.slice(1)); } catch { return; }
      const target = document.getElementById(id);
      if (!target) return;
      let node: HTMLElement | null = target;
      while (node) {
        if (node instanceof HTMLDetailsElement) node.open = true;
        node = node.parentElement;
      }
      target.scrollIntoView({block:"start"});
    }
    reveal(); window.addEventListener("hashchange",reveal);
    return () => window.removeEventListener("hashchange",reveal);
  }, []);
  return null;
}
