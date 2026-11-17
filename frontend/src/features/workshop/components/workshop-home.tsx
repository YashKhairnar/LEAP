"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getWorkshopState, rememberResearchId, type WorkshopState } from "@/features/workshop/lib/workshop-api";
import { WORKSHOP_HREF } from "@/features/workshop/lib/visibility";

const PARTS = 7; // Before you start + Steps 1–6

/** Dashboard body while only the workshop is shown. */
export default function WorkshopHome({ onResearchId }: { onResearchId?: (researchId: string | null) => void }) {
  const [state, setState] = useState<WorkshopState | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    void getWorkshopState().then((value) => {
      if (!active) return;
      setState(value);
      if (value.research_id) { rememberResearchId(value.research_id); onResearchId?.(value.research_id); }
    }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [onResearchId]);

  const done = state?.completed_stages.filter((stage) => stage !== "finish").length ?? 0;
  const started = Boolean(state && (done > 0 || Object.keys(state.cells).length > 0));
  const percent = state?.workshop_complete ? 100 : Math.round((done / PARTS) * 100);
  const status = state?.workshop_complete ? "Completed" : started ? "In progress" : "Not started";

  return <section className="simple-dashboard-content" aria-labelledby="paths-title">
    <header className="simple-page-heading">
      <h1 id="paths-title">{started ? "Welcome back" : "Machine Learning Workshop"}</h1>
      <p>{started ? "Pick up where you left off." : "Build a model that reads a restaurant review and decides whether it is positive or negative."}</p>
    </header>
    <section className="path-section" aria-labelledby="workshop-path-title">
      <div className="simple-path-list">
        <article className="simple-path">
          <div className="path-card-status">
            <span className={`path-status ${started ? "started" : ""}`}>{failed ? "Progress unavailable" : status}</span>
            <span className="path-percent">{percent}% complete</span>
          </div>
          <h3 id="workshop-path-title">Classifying restaurant reviews</h3>
          <p>Load 10,000 real reviews, split them, turn text into numbers, train a LinearSVC model and test it on reviews it has never seen.</p>
          <p className="simple-path-meta">Beginner · about 1–2 hours{state ? ` · ${state.workshop_version.label}` : ""}</p>
          <div className="path-card-progress" role="progressbar" aria-label="Workshop progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}><span style={{ width: `${percent}%` }} /></div>
          <span className="path-stage-count">{done} of {PARTS} parts</span>
          <Link className="path-link" href={WORKSHOP_HREF}>{state?.workshop_complete ? "Review" : started ? "Continue" : "Start"} <span aria-hidden="true">→</span></Link>
        </article>
      </div>
    </section>
    <section className="how-paths-work" aria-labelledby="how-workshop-works-title">
      <h2 id="how-workshop-works-title">How the workshop works</h2>
      <ol>
        <li><strong>Before you start.</strong> Learn how to run a cell, then read what machine learning is.</li>
        <li><strong>Six steps.</strong> Each step explains an idea, then gives you short pieces of code to copy, paste and run.</li>
        <li><strong>Check your understanding.</strong> Each step ends with short questions to answer in your own words.</li>
        <li><strong>Finish.</strong> Complete the post-survey and the completion checklist.</li>
      </ol>
      <p>Your code runs and answers are saved under your research ID as you go. Enter the same ID to come back later.</p>
    </section>
  </section>;
}
