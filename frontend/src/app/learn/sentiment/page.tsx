"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AdaptiveQuestion from "./adaptive-question";
import { questionBanks, sentimentStages, type QuestionItem, type StepId } from "@/lib/question-bank";
import { enqueueCollection, flushCollectionQueue, learningSessionId } from "@/lib/collection";
import LogoutButton from "@/components/logout-button";

const lessonSteps: { id: StepId; label: string }[] = [
  { id: "activate", label: "Activate" }, { id: "connect", label: "Connect" },
  { id: "implement", label: "Implement" }, { id: "learn", label: "Learn" },
  { id: "practice", label: "Practice" }, { id: "review", label: "Review" },
];
const stepTitles: Record<StepId, string> = {
  activate: "Start with what you know", connect: "Connect familiar and new structures",
  implement: "Complete the pipeline code", learn: "Draw the concept boundary",
  practice: "Apply the idea independently", review: "Confirm and transfer your understanding",
};
const emptyMastery = (): Record<StepId, boolean> => ({ activate: false, connect: false, implement: false, learn: false, practice: false, review: false });

export default function SentimentLesson() {
  const [stageIndex, setStageIndex] = useState(0);
  const [completedStages, setCompletedStages] = useState(0);
  const [step, setStep] = useState(0);
  const [furthestStep, setFurthestStep] = useState(0);
  const [mastered, setMastered] = useState<Record<StepId, boolean>>(emptyMastery);
  const [showAnalogy, setShowAnalogy] = useState(false);
  const [confidence, setConfidence] = useState<string | null>(null);
  const [taskComplete, setTaskComplete] = useState(false);
  const [sessionId] = useState(() => typeof window === "undefined" ? "" : learningSessionId());
  const [eventCount, setEventCount] = useState(0);
  const stage = sentimentStages[stageIndex];
  const current = lessonSteps[step];

  useEffect(() => { void flushCollectionQueue().catch((error) => console.warn("Pending learner events will retry later.", error)); }, []);

  const recordBehavior = (eventType: "content_exposure" | "confidence_checkpoint" | "navigation", data: Record<string, unknown>, locationStep = current.id) => {
    setEventCount((count) => count + 1);
    void enqueueCollection({ endpoint: "/api/events", payload: {
      event_id: crypto.randomUUID(), session_id: sessionId, event_type: eventType,
      location: { task: "sentiment_classification", stage: stage.id, step: locationStep },
      event_timestamp: new Date().toISOString(), data,
    }}).catch((error) => console.warn("Learner event queued for retry.", error));
  };

  const recordAttempt = (item: QuestionItem, answer: string, correct: boolean, attempt: number, responseTimeMs: number) => {
    const stepIndex = lessonSteps.findIndex((lessonStep) => lessonStep.id === item.step);
    const isReview = item.step === "review";
    const decision = correct ? (isReview ? "remain_on_step" : "advance_step") : "remain_on_step";
    const locationAfter = correct
      ? isReview
        ? { task: "sentiment_classification", stage: stage.id, step: "review" }
        : { task: "sentiment_classification", stage: stage.id, step: lessonSteps[stepIndex + 1].id }
      : { task: "sentiment_classification", stage: stage.id, step: item.step };
    const contentId = `sentiment.${item.id}`;
    const transition = {
      transition_id: crypto.randomUUID(), session_id: sessionId,
      location_before: { task: "sentiment_classification", stage: stage.id, step: item.step },
      instructional_action: { action_type: item.actionType, content_id: contentId },
      learner_action: { response: answer },
      observation: { correct, score: correct ? 1 : 0, attempt, response_time_ms: responseTimeMs, misconception: correct ? null : item.misconception },
      progression: { decision }, location_after: locationAfter,
      event_timestamp: new Date().toISOString(), selection_policy: "predefined_sequence_v1",
    };
    setEventCount((count) => count + 1);
    void enqueueCollection({ endpoint: "/api/interactions", payload: { ...transition, content: {
      content_id: contentId, task: "sentiment_classification", stage: stage.id, step: item.step,
      action_type: item.actionType, prompt: item.prompt, options: item.options,
      correct_answer: item.correctAnswer, explanation: item.explanation,
      misconception: item.misconception, learning_objectives: item.learningObjectives ?? stage.objectives,
    }}}).catch((error) => console.warn("Interaction queued for retry.", error));
    if (correct) setMastered((state) => ({ ...state, [item.step]: true }));
  };

  const moveTo = (index: number) => {
    if (index > furthestStep || taskComplete) return;
    if (index !== step) recordBehavior("navigation", { direction: index < step ? "previous" : "direct", from_step: current.id, to_step: lessonSteps[index].id });
    setStep(index);
    document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const continueLesson = () => {
    const next = step + 1;
    recordBehavior("navigation", { direction: "continue", from_step: current.id, to_step: lessonSteps[next].id });
    setFurthestStep((value) => Math.max(value, next)); setStep(next); setShowAnalogy(false);
  };

  const completeStage = () => {
    const finalStage = stageIndex === sentimentStages.length - 1;
    recordBehavior("navigation", { direction: finalStage ? "complete_task" : "complete_stage", from_stage: stage.id, to_stage: finalStage ? null : sentimentStages[stageIndex + 1].id, completed_stages: stageIndex + 1, total_stages: sentimentStages.length });
    setCompletedStages(stageIndex + 1);
    if (finalStage) { setTaskComplete(true); return; }
    setStageIndex((value) => value + 1); setStep(0); setFurthestStep(0); setMastered(emptyMastery()); setConfidence(null); setShowAnalogy(false);
    requestAnimationFrame(() => document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  return <main className="site-shell">
    <header className="topbar"><Link className="brand" href="/" aria-label="LEAP home"><span>LEAP</span></Link><div className="header-context"><Link className="back-link" href="/">← All learning paths</Link><span>Sentiment classification</span></div><nav className="account-nav"><span className="streak"><span className="streak-dot" /> {eventCount} learner signals</span><LogoutButton /></nav></header>

    <section className="progress-section" aria-labelledby="path-title"><div className="progress-heading"><div><p className="eyebrow">Your learning path</p><h1 id="path-title">Build a sentiment classifier</h1></div><p className="path-count"><strong>{Math.min(stageIndex + 1, 6)}</strong> of 6 stages</p></div><ol className="stage-track">{sentimentStages.map((item, index) => <li className={`stage ${index < completedStages ? "complete-stage" : index === stageIndex ? "active" : "locked"}`} key={item.id}><span className="stage-node">{index < completedStages ? "✓" : index + 1}</span><span className="stage-copy"><span>Stage {index + 1}</span><strong>{item.shortLabel}</strong></span></li>)}</ol></section>

    <section className="lesson-header" id="lesson"><div className="lesson-title-row"><div><p className="eyebrow blue">Stage {stageIndex + 1} · {stage.shortLabel}</p><h2>{stage.heading}</h2><p className="lesson-intro">{stage.intro}</p></div><div className="time-estimate"><ClockIcon /> 10–15 min</div></div><ol className="lesson-steps">{lessonSteps.map((item, index) => <li key={item.id}><button disabled={index > furthestStep || taskComplete} className={index === step ? "lesson-step current" : mastered[item.id] ? "lesson-step complete" : index > furthestStep ? "lesson-step locked-step" : "lesson-step"} onClick={() => moveTo(index)}><span>{mastered[item.id] ? <CheckIcon /> : index + 1}</span>{item.label}</button></li>)}</ol></section>

    <article className="lesson-content">
      <div className="section-number">0{step + 1}</div><p className="eyebrow">{current.label}</p><h3>{stepTitles[current.id]}</h3><p className="lead">{stage.intro}</p>
      <div className="comparison-grid"><section className="mapping-panel"><p className="panel-kicker">Familiar structure</p><h4>{stage.familiar}</h4><dl className="mapping-list"><div><dt>What you know</dt><dd>{stage.familiar}</dd></div><div><dt>What it becomes</dt><dd>{stage.target}</dd></div><div><dt>Key relationship</dt><dd>{stage.relationship}</dd></div></dl></section><section className="code-block dark"><div className="code-heading"><span className="language-dot python" /> Python · Stage {stageIndex + 1}</div><pre><code>{stage.pythonCode}</code></pre></section></div>
      <div className="transfer-strip"><div><span className="transfer-index">01</span><p><strong>You already know</strong>{stage.familiar}</p></div><div><span className="transfer-index">02</span><p><strong>What transfers</strong>{stage.relationship}</p></div><div><span className="transfer-index">03</span><p><strong>What is new</strong>{stage.target}</p></div></div>
      {(current.id === "connect" || current.id === "implement") && <section className={showAnalogy ? "analogy open" : "analogy"}><button onClick={() => { const opening = !showAnalogy; setShowAnalogy(opening); if (opening) recordBehavior("content_exposure", { content_id: `sentiment.${stage.id}.analogy`, exposure: "opened" }); }}><span className="analogy-icon"><BulbIcon /></span><span><small>Optional instructional content</small>Open the stage analogy</span><ChevronIcon open={showAnalogy} /></button>{showAnalogy && <p>{stage.analogy}</p>}</section>}
      {current.id === "review" && <blockquote className="transfer-statement">“{stage.reviewStatement}”</blockquote>}
      {!taskComplete && <AdaptiveQuestion key={`${stage.id}.${current.id}`} items={questionBanks[stage.id][current.id]} onAttempt={recordAttempt} />}
      {current.id === "review" && mastered.review && !taskComplete && <fieldset className="confidence-check"><legend>How confident are you in this stage?</legend><div>{["Not yet", "Somewhat", "Confident"].map((level) => <button type="button" className={confidence === level ? "confidence selected" : "confidence"} onClick={() => { setConfidence(level); recordBehavior("confidence_checkpoint", { confidence: level, stage: stage.id }); }} key={level}>{level}</button>)}</div></fieldset>}
      {taskComplete && <section className="task-complete"><CheckIcon /><p className="eyebrow">Task completed</p><h3>Sentiment-classification pipeline mastered</h3><p>You completed all six stages. The full ordered trajectory is ready in the collection backend.</p><Link className="overview-cta" href="/">Return to dashboard</Link></section>}
      {!taskComplete && <footer className="lesson-footer"><button className="text-button" disabled={step === 0} onClick={() => moveTo(step - 1)}>← Previous</button><span>Step {step + 1} of {lessonSteps.length}</span>{step < lessonSteps.length - 1 ? <button className="primary-button" disabled={!mastered[current.id]} onClick={continueLesson}>Continue <span>→</span></button> : <button className="primary-button" disabled={!mastered.review || !confidence} onClick={completeStage}>{stageIndex === 5 ? "Complete task" : "Next stage"} <span>→</span></button>}</footer>}
    </article>
  </main>;
}

function ClockIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>; }
function CheckIcon() { return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 10 3 3 7-7"/></svg>; }
function BulbIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18h6M10 22h4M8.5 14.5A6 6 0 1 1 15.5 14.5c-.8.7-1.3 1.4-1.5 2.5h-4c-.2-1.1-.7-1.8-1.5-2.5Z"/></svg>; }
function ChevronIcon({ open }: { open: boolean }) { return <svg className={open ? "chevron rotated" : "chevron"} viewBox="0 0 20 20" aria-hidden="true"><path d="m6 8 4 4 4-4"/></svg>; }
