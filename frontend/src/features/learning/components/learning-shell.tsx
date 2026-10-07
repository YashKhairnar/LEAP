"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";
import LogoutButton from "@/components/logout-button";
import CollectionSyncStatus from "@/features/collection/components/collection-sync-status";

export default function LearningShell({ taskTitle, navigator, children }: {
  taskTitle: string;
  overviewHref?: string;
  navigator: ReactNode;
  children: ReactNode;
}) {
  const [pathHidden, setPathHidden] = useState(false);
  const preferenceRestored = useRef(false);

  useEffect(() => {
    const storedPreference = window.localStorage.getItem("leap.ui.curriculum.hidden");
    const savedPreference = storedPreference === null ? window.matchMedia("(max-width: 1000px)").matches : storedPreference === "true";
    const restoreTimer = window.setTimeout(() => {
      setPathHidden(savedPreference);
      preferenceRestored.current = true;
    }, 0);
    return () => window.clearTimeout(restoreTimer);
  }, []);

  useEffect(() => {
    if (!preferenceRestored.current) return;
    window.localStorage.setItem("leap.ui.curriculum.hidden", String(pathHidden));
  }, [pathHidden]);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !pathHidden) setPathHidden(true);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [pathHidden]);

  return (
    <main className="site-shell learning-site-shell">
      <header className="topbar learning-topbar">
        <div className="header-context">
          <Link className="back-link" href={"/"}>{"← Learning paths"}</Link>
          <span>{taskTitle}</span>
        </div>
        <Link className="brand" href="/" aria-label="LEAP dashboard"><span>LEAP</span></Link>
        <div className="account-controls"><LogoutButton /></div>
      </header>
      <CollectionSyncStatus />

      <div className={`learning-workspace-shell ${pathHidden ? "path-panel-hidden" : ""}`} onClick={(event) => { if ((event.target === event.currentTarget || (event.target instanceof Element && event.target.closest("[data-stage-navigation]"))) && window.matchMedia("(max-width: 1000px)").matches) setPathHidden(true); }}>
        <button
          className={`curriculum-visibility-toggle ${pathHidden ? "is-collapsed" : ""}`}
          type="button"
          aria-controls="learning-path-panel"
          aria-expanded={!pathHidden}
          aria-label={pathHidden ? "Show curriculum" : "Hide curriculum"}
          title={pathHidden ? "Show curriculum" : "Hide curriculum"}
          onClick={() => setPathHidden((hidden) => !hidden)}
        >
          <EyeIcon crossed={!pathHidden} />
        </button>
        {navigator}
        {children}
      </div>
    </main>
  );
}

function EyeIcon({ crossed }: { crossed: boolean }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/>{crossed && <path d="m4 4 16 16"/>}</svg>;
}
