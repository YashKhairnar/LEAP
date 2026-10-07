"use client";

import { useEffect, useRef, useState } from "react";
import GeneratedTutorCard from "@/features/learning/components/generated-tutor-card";
import CompletedStagePicker from "@/features/learning/components/completed-stage-picker";
import CircularProgress from "@/components/ui/circular-progress";
import { INSTRUCTIONAL_ACTIONS, type InstructionalStep } from "@/features/learning/lib/instructional-actions";
import type { StageIntroduction } from "@/features/learning/lib/lesson-introductions";

const steps: { id: InstructionalStep; label: string }[] = [
  { id: "connect", label: "Bridge" },
  { id: "practice", label: "Apply" },
  { id: "review", label: "Check" },
];
const ignorePresentation = () => {};
const ignoreAttempt = async () => {};

export default function CompletedStageReview({ task, stage, stageNumber, progress, taskComplete, onReturn, completedStages, onSelectStage, initialStepIndex = 0 }: {
  task: string;
  stage: StageIntroduction;
  stageNumber: number;
  progress: number;
  taskComplete: boolean;
  onReturn: () => void;
  completedStages: StageIntroduction[];
  onSelectStage: (stageId: string) => void;
  initialStepIndex?: number;
}) {
  const [stepIndex, setStepIndex] = useState(initialStepIndex);
  const heading = useRef<HTMLHeadingElement>(null);
  const step = steps[stepIndex];
  useEffect(() => { heading.current?.focus({ preventScroll: true }); }, []);

  return <article className="lesson-content" id="lesson">
    <CompletedStagePicker stages={completedStages} selectedStage={stage.id} onSelect={onSelectStage} />
    <header className="lesson-context-header">
      <div><p className="eyebrow blue">Stage {stageNumber} · Completed</p><h2 ref={heading} tabIndex={-1}>{stage.title}</h2></div>
      <CircularProgress value={progress} />
    </header>
    <nav className="completed-review-nav" aria-label="Review lesson steps">
      {steps.map((item, index) => <button key={item.id} type="button" aria-current={index === stepIndex ? "step" : undefined} onClick={() => setStepIndex(index)}>{item.label}</button>)}
    </nav>
    <GeneratedTutorCard key={step.id} task={task} stage={stage.id} step={step.id} actionType={INSTRUCTIONAL_ACTIONS[step.id][0]} lessonContext={stage.summary} learningObjectives={stage.objectives} onAttempt={ignoreAttempt} onPresented={ignorePresentation} reviewOnly />
    <footer className="lesson-footer">
      <div className="review-footer-actions">
        <button type="button" className="text-button" disabled={stepIndex === 0 && stageNumber === 1} onClick={() => { if (stepIndex > 0) setStepIndex((index) => index - 1); else onSelectStage(completedStages[stageNumber - 2].id); }}>← Previous</button>
        <button type="button" className="text-button" onClick={onReturn}>{taskComplete ? "Completed task" : "Current stage"}</button>
      </div>
      {stepIndex < steps.length - 1 && <button type="button" className="primary-button" onClick={() => setStepIndex((index) => index + 1)}>Next step <span aria-hidden="true">→</span></button>}
    </footer>
  </article>;
}
