"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import LogoutButton from "@/components/logout-button";
import AdaptiveQuestion from "@/app/learn/sentiment/adaptive-question";
import { additionalQuestionBank, type AdditionalTask } from "@/lib/additional-task-bank";
import type { QuestionItem } from "@/lib/question-bank";
import { learningSessionId, enqueueCollection } from "@/lib/collection";
import type { InstructionalStep } from "@/lib/instructional-actions";

const steps: { id: InstructionalStep; label: string }[] = [
  { id: "activate", label: "Activate" }, { id: "connect", label: "Connect" }, { id: "implement", label: "Implement" },
  { id: "learn", label: "Learn" }, { id: "practice", label: "Practice" }, { id: "review", label: "Review" },
];

export default function TaskLessonClient({ task }: { task: AdditionalTask }) {
  const [stageIndex, setStageIndex] = useState(0);
  const [stepIndex, setStepIndex] = useState(0);
  const [mastered, setMastered] = useState<Record<string, boolean>>({});
  const [completedStages, setCompletedStages] = useState(0);
  const [taskComplete, setTaskComplete] = useState(false);
  const [sessionId] = useState(() => typeof window === "undefined" ? "" : learningSessionId());
  const stage = task.stages[stageIndex];
  const step = steps[stepIndex];
  const bank = useMemo(() => additionalQuestionBank(task, stage), [task, stage]);

  const recordPresentation = (item: QuestionItem, presentationId: string) => {
    const contentId = `${task.id}.${item.id}`;
    void enqueueCollection({ endpoint: "/api/events", payload: {
      event_id: presentationId, session_id: sessionId, event_type: "content_presented",
      location: { task: task.id, stage: stage.id, step: item.step }, event_timestamp: new Date().toISOString(),
      data: { presentation_id: presentationId, content_id: contentId, action_type: item.actionType, content: { prompt: item.prompt, options: item.options, correct_answer: item.correctAnswer, explanation: item.explanation, misconception: item.misconception, learning_objectives: item.learningObjectives ?? [] } },
    }}).catch((error) => console.warn("Content presentation queued for retry.", error));
  };

  const recordAttempt = (item: QuestionItem, answer: string, correct: boolean, attempt: number, responseTimeMs: number, presentationId: string) => {
    const nextStep = steps[Math.min(stepIndex + 1, steps.length - 1)].id;
    const contentId = `${task.id}.${item.id}`;
    void enqueueCollection({ endpoint: "/api/interactions", payload: {
      session_id: sessionId,
      content: { content_id: contentId, task: task.id, stage: stage.id, step: item.step, action_type: item.actionType, prompt: item.prompt, options: item.options, correct_answer: item.correctAnswer, explanation: item.explanation, misconception: item.misconception, learning_objectives: item.learningObjectives ?? [] },
      transition_id: crypto.randomUUID(),
      location_before: { task: task.id, stage: stage.id, step: item.step },
      instructional_action: { action_type: item.actionType, content_id: contentId }, learner_action: { response: answer },
      observation: { correct, score: correct ? 1 : 0, attempt, response_time_ms: responseTimeMs, misconception: correct ? null : item.misconception },
      progression: { decision: correct && item.step !== "review" ? "advance_step" : "remain_on_step" },
      location_after: { task: task.id, stage: stage.id, step: correct ? nextStep : item.step },
      event_timestamp: new Date().toISOString(), selection_policy: "predefined_sequence_v1", presentation_id: presentationId,
    }}).catch((error) => console.warn("Interaction queued for retry.", error));
    if (correct) setMastered((current) => ({ ...current, [`${stage.id}.${item.step}`]: true }));
  };

  const finishStage = () => {
    const final = stageIndex === task.stages.length - 1;
    void enqueueCollection({ endpoint: "/api/events", payload: { event_id: crypto.randomUUID(), session_id: sessionId, event_type: "navigation", location: { task: task.id, stage: stage.id, step: "review" }, event_timestamp: new Date().toISOString(), data: { direction: final ? "complete_task" : "complete_stage", from_stage: stage.id, to_stage: final ? null : task.stages[stageIndex + 1].id, completed_stages: stageIndex + 1, total_stages: task.stages.length } } }).catch(() => undefined);
    setCompletedStages(stageIndex + 1);
    if (final) { setTaskComplete(true); return; }
    setStageIndex((value) => value + 1); setStepIndex(0);
  };

  const masteredCurrent = mastered[`${stage.id}.${step.id}`];
  return <main className="site-shell">
    <header className="topbar"><Link className="brand" href="/"><span>LEAP</span></Link><div className="header-context"><Link className="back-link" href="/">← All learning paths</Link><span>{task.title}</span></div><div className="account-controls"><LogoutButton /></div></header>
    <section className="progress-section"><div className="progress-heading"><div><p className="eyebrow">Your learning path</p><h1>{task.title}</h1></div><p className="path-count"><strong>{stageIndex + 1}</strong> of 6 stages</p></div><ol className="stage-track">{task.stages.map((item, index) => <li className={`stage ${index < completedStages ? "complete-stage" : index === stageIndex ? "active" : "locked"}`} key={item.id}><span className="stage-node">{index < completedStages ? "✓" : index + 1}</span><span className="stage-copy"><span>Stage {index + 1}</span><strong>{item.label}</strong></span></li>)}</ol></section>
    <section className="lesson-header"><div className="lesson-title-row"><div><p className="eyebrow blue">Stage {stageIndex + 1} · {stage.label}</p><h2>{stage.title}</h2><p className="lesson-intro">{stage.intro}</p></div></div><ol className="lesson-steps">{steps.map((item, index) => <li key={item.id}><button disabled={index > stepIndex} className={index === stepIndex ? "lesson-step current" : mastered[`${stage.id}.${item.id}`] ? "lesson-step complete" : "lesson-step locked-step"} onClick={() => index <= stepIndex && setStepIndex(index)}><span>{index + 1}</span>{item.label}</button></li>)}</ol></section>
    <article className="lesson-content"><div className="section-number">0{stepIndex + 1}</div><p className="eyebrow">{step.label}</p><h3>{stage.title}</h3><p className="lead">{stage.intro}</p><section className="code-block dark"><div className="code-heading"><span className="language-dot python" /> Python · Stage {stageIndex + 1}</div><pre><code>{stage.code}</code></pre></section>
      {!taskComplete && <AdaptiveQuestion key={`${stage.id}.${step.id}`} items={bank[step.id]} onAttempt={recordAttempt} onPresented={recordPresentation} />}
      {taskComplete ? <section className="task-complete"><p className="eyebrow">Task completed</p><h3>{task.title} completed</h3><p>The complete ordered learner trajectory has been sent to the collection backend.</p><Link className="overview-cta" href="/">Return to dashboard</Link></section> : <footer className="lesson-footer"><button className="text-button" disabled={stepIndex === 0} onClick={() => setStepIndex((value) => value - 1)}>← Previous</button><span>Step {stepIndex + 1} of 6</span>{stepIndex < 5 ? <button className="primary-button" disabled={!masteredCurrent} onClick={() => setStepIndex((value) => value + 1)}>Continue <span>→</span></button> : <button className="primary-button" disabled={!masteredCurrent} onClick={finishStage}>{stageIndex === 5 ? "Complete task" : "Next stage"} <span>→</span></button>}</footer>}
    </article>
  </main>;
}
