"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";
import LogoutButton from "@/components/logout-button";
import CollectionSyncStatus from "@/features/collection/components/collection-sync-status";

export default function LearningShell({ taskTitle, location, progress, navigator, children }: {
  taskTitle: string;
  location?: string;
  progress?: number;
  overviewHref?: string;
  navigator: ReactNode;
  children: ReactNode;
}) {
  const [pathHidden, setPathHidden] = useState(true);
  const preferenceRestored = useRef(false);

  useEffect(() => {
    const storedPreference = window.localStorage.getItem("leap.ui.curriculum.hidden");
    // On narrow screens the path is an overlay drawer, so it always starts closed.
    const savedPreference = window.matchMedia("(max-width: 1000px)").matches || storedPreference === null ? true : storedPreference === "true";
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
      <header className="learning-header">
        <div className="learning-header-row">
          <Link className="learning-home-link" href="/"><ArrowLeftIcon /><span>Home</span></Link>
          <div className="learning-header-title">
            <span>{taskTitle}</span>
            {location && <strong>{location}</strong>}
          </div>
          <button className="path-menu-button" type="button" aria-controls="learning-path-panel" aria-expanded={!pathHidden} onClick={() => setPathHidden((hidden) => !hidden)}><MenuIcon /><span>{pathHidden ? "All stages" : "Close stages"}</span></button>
          <LogoutButton />
        </div>
        {progress !== undefined && <div className="learning-header-progress" role="progressbar" aria-label="Course progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}><span style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} /></div>}
      </header>
      <CollectionSyncStatus />

      <div className={`learning-workspace-shell ${pathHidden ? "path-panel-hidden" : ""}`} onClick={(event) => { if ((event.target === event.currentTarget || (event.target instanceof Element && event.target.closest("[data-stage-navigation]"))) && window.matchMedia("(max-width: 1000px)").matches) setPathHidden(true); }}>
        {navigator}
        {children}
      </div>
    </main>
  );
}

function ArrowLeftIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5m6-6-6 6 6 6" /></svg>; }
function MenuIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h10" /></svg>; }
