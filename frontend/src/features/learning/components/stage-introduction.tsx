"use client";

import { useEffect, useRef } from "react";
import type { StageIntroduction } from "@/features/learning/lib/lesson-introductions";

export default function StageIntroduction({ stage, stageNumber, totalStages, onStart, onPrevious, resuming }: {
  stage: StageIntroduction;
  stageNumber: number;
  totalStages: number;
  onStart: () => void;
  onPrevious?: () => void;
  resuming: boolean;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus({ preventScroll: true }); }, [stage.id]);

  return <section className="stage-introduction" aria-labelledby="stage-briefing-title">
    <p className="intro-kicker">Stage {stageNumber} of {totalStages} · Before you begin</p>
    <h3 ref={heading} tabIndex={-1} id="stage-briefing-title">What you’ll learn</h3>
    <ul className="stage-intro-objectives">{stage.objectives.map((objective) => <li key={objective}>{objective}</li>)}</ul>
    <p className="stage-intro-plan">You’ll connect the idea to familiar examples, try a guided exercise, and check your understanding.</p>
    <footer>
      {onPrevious ? <button className="text-button" type="button" onClick={onPrevious}>← Previous stage</button> : resuming && <p>Your saved step is ready.</p>}
      <button className="intro-primary" type="button" onClick={onStart}>{resuming ? "Continue lesson" : "Begin lesson"}<span aria-hidden="true">→</span></button>
    </footer>
  </section>;
}
