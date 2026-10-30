"use client";
import { useEffect, useState } from "react";
import { ScriptBrowser } from "./ScriptBrowser";
import { ArgokajReader } from "./ArgokajReader";

export function Reader() {
  const [comparison, setComparison] = useState<boolean | null>(null);
  useEffect(() => {
    const read = () => setComparison(new URL(window.location.href).searchParams.get("compare") === "argokaj");
    read(); window.addEventListener("popstate",read);
    return () => window.removeEventListener("popstate",read);
  }, []);
  function toggle(value: boolean) {
    const url = new URL(window.location.href);
    if (value) url.searchParams.set("compare","argokaj");
    else {
      url.searchParams.delete("compare"); url.searchParams.delete("errors");
      const sid = url.searchParams.get("script") || "1001";
      url.searchParams.set("route",`section-${sid[0]}`); url.hash = "";
    }
    window.history.pushState(null,"",url); setComparison(value);
  }
  if (comparison === null) return <p className="script-status">Loading reader…</p>;
  if (comparison) return <ArgokajReader onClose={() => toggle(false)} />;
  return <><div className="shell argokaj-entry"><label><input type="checkbox" checked={false} onChange={() => toggle(true)} /> Display Argokaj for comparison</label><a href="../audit/">Translation audit →</a></div><ScriptBrowser /></>;
}
