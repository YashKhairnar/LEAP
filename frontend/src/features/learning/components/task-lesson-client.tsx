"use client";

import Link from "next/link";
import type { AttemptEvidence } from "@/features/collection/lib/question-exposure";
import { useEffect, useMemo, useState } from "react";
import { additionalQuestionBank, type AdditionalTask } from "@/features/learning/lib/additional-task-bank";
import type { QuestionItem } from "@/features/learning/lib/question-bank";
import { learningSessionId, enqueueCollection } from "@/features/collection/lib/collection";
import type { InstructionalStep } from "@/features/learning/lib/instructional-actions";
import { questionContentId } from "@/features/collection/lib/content-id";
import GeneratedTutorCard from "@/features/learning/components/generated-tutor-card";
import { getTaskProgress } from "@/lib/auth";
import { flushCollectionQueue } from "@/features/collection/lib/collection";
import LearningShell from "@/features/learning/components/learning-shell";
import CompletedStageReview from "@/features/learning/components/completed-stage-review";
import CompletedStagePicker from "@/features/learning/components/completed-stage-picker";
import CircularProgress from "@/components/ui/circular-progress";
import TaskAssessment, { AssessmentNavigation } from "@/features/assessment/components/task-assessment";
import { taskIntroductions } from "@/features/learning/lib/lesson-introductions";

const steps: { id: InstructionalStep; label: string }[] = [
  { id: "connect", label: "Bridge" },
  { id: "practice", label: "Apply" },
  { id: "review", label: "Check" },
];

export default function TaskLessonClient({ task, initialReviewStage }: { task: AdditionalTask; initialReviewStage?: string }) {
  const [stageIndex, setStageIndex] = useState(0);
  const [stepIndex, setStepIndex] = useState(0);
  const [mastered, setMastered] = useState<Record<string, boolean>>({});
  const [completedStages, setCompletedStages] = useState(0);
  const [taskComplete, setTaskComplete] = useState(false);
  const [furthestStep, setFurthestStep] = useState(0);
  const [progressRestored, setProgressRestored] = useState(false);
  const [reviewStageIndex, setReviewStageIndex] = useState<number | null>(null);
  const [reviewInitialStep, setReviewInitialStep] = useState(0);
  const [sessionId] = useState(() => typeof window === "undefined" ? "" : learningSessionId());
  const stage = task.stages[stageIndex];
  const step = steps[stepIndex];
  const overallProgress = taskComplete ? 100 : Math.round(((stageIndex * steps.length + stepIndex) / (task.stages.length * steps.length)) * 100);
  const bank = useMemo(() => additionalQuestionBank(task, stage), [task, stage]);

  useEffect(() => {
    let active = true;
    void flushCollectionQueue().catch(() => undefined).then(() => getTaskProgress()).then((records) => {
      if (!active) return;
      const saved = records.find((record) => record.task === task.id);
      if (saved) {
        const savedStage = task.stages.findIndex((item) => item.id === saved.current_stage);
        const restoredStage = savedStage >= 0 ? savedStage : Math.min(saved.completed_stages, task.stages.length - 1);
        const savedStep = steps.findIndex((item) => item.id === saved.current_step);
        const restoredStep = savedStep >= 0 ? savedStep : 0;
        const restoredMastery: Record<string, boolean> = {};
        steps.slice(0, restoredStep).forEach((item) => { restoredMastery[`${task.stages[restoredStage].id}.${item.id}`] = true; });
        setStageIndex(restoredStage); setStepIndex(restoredStep); setFurthestStep(restoredStep);
        setMastered(restoredMastery); setCompletedStages(saved.completed_stages); setTaskComplete(saved.task_complete);
        const requestedReview = task.stages.findIndex((item) => item.id === initialReviewStage);
        if (requestedReview >= 0 && requestedReview < saved.completed_stages) { setReviewInitialStep(0); setReviewStageIndex(requestedReview); }
      }
      setProgressRestored(true);
    }).catch(() => { if (active) setProgressRestored(true); });
    return () => { active = false; };
  }, [task, initialReviewStage]);

  const moveStep = (next: number) => {
    if (next < 0 || next > furthestStep || taskComplete) return;
    void enqueueCollection({ endpoint: "/api/events", payload: {
      event_id: crypto.randomUUID(), session_id: sessionId, event_type: "navigation",
      location: { task: task.id, stage: stage.id, step: step.id }, event_timestamp: new Date().toISOString(),
      data: { direction: next < stepIndex ? "previous" : "direct", from_step: step.id, to_step: steps[next].id },
    }}).catch(() => undefined);
    setStepIndex(next);
  };

  const continueStep = () => {
    const next = stepIndex + 1;
    void enqueueCollection({ endpoint: "/api/events", payload: {
      event_id: crypto.randomUUID(), session_id: sessionId, event_type: "navigation",
      location: { task: task.id, stage: stage.id, step: step.id }, event_timestamp: new Date().toISOString(),
      data: { direction: "continue", from_step: step.id, to_step: steps[next].id },
    }}).catch(() => undefined);
    setFurthestStep((value) => Math.max(value, next)); setStepIndex(next);
  };

  const recordPresentation = (item: QuestionItem, presentationId: string) => {
    const contentId = questionContentId(task.id, item);
    void enqueueCollection({ endpoint: "/api/events", payload: {
      event_id: presentationId, session_id: sessionId, event_type: "content_presented",
      location: { task: task.id, stage: stage.id, step: item.step }, event_timestamp: new Date().toISOString(),
      data: { presentation_id: presentationId, content_id: contentId, action_type: item.actionType, selection_policy: item.selectionPolicy ?? "llm_generated_content_v1", planner_decision: item.plannerDecision, generation_metadata: item.generationMetadata, content: { prompt: item.prompt, options: item.options, correct_answer: item.correctAnswer, explanation: item.explanation, misconception: item.misconception, learning_objectives: item.learningObjectives ?? [], lesson_content: item.lessonContent } },
    }}).catch((error) => console.warn("Content presentation queued for retry.", error));
  };

  const recordAttempt = async (item: QuestionItem, answer: string, correct: boolean, attempt: number, responseTimeMs: number, presentationId: string, evidence: AttemptEvidence) => {
    const nextStep = steps[Math.min(stepIndex + 1, steps.length - 1)].id;
    const contentId = questionContentId(task.id, item);
    void enqueueCollection({ endpoint: "/api/interactions", payload: {
      session_id: sessionId,
      content: item.collectionContent ?? { content_id: contentId, task: task.id, stage: stage.id, step: item.step, action_type: item.actionType, prompt: item.prompt, options: item.options, correct_answer: item.correctAnswer, explanation: item.explanation, misconception: item.misconception, learning_objectives: item.learningObjectives ?? [], lesson_content: item.lessonContent, planner_decision: item.plannerDecision, generation_metadata: item.generationMetadata },
      transition_id: crypto.randomUUID(),
      location_before: { task: task.id, stage: stage.id, step: item.step },
      instructional_action: { action_type: item.actionType, content_id: contentId }, learner_action: { response: answer },
      observation: { ...evidence, correct, score: correct ? 1 : 0, attempt, response_time_ms: responseTimeMs, misconception: correct ? null : item.misconception },
      progression: { decision: correct && item.step !== "review" ? "advance_step" : "remain_on_step" },
      location_after: { task: task.id, stage: stage.id, step: correct ? nextStep : item.step },
      event_timestamp: new Date().toISOString(), selection_policy: item.selectionPolicy ?? "llm_generated_content_v1", presentation_id: presentationId,
    }}).catch((error) => console.warn("Interaction queued for retry.", error));
    if (correct) setMastered((current) => ({ ...current, [`${stage.id}.${item.step}`]: true }));
  };

  const finishStage = () => {
    const final = stageIndex === task.stages.length - 1;
    void enqueueCollection({ endpoint: "/api/events", payload: { event_id: crypto.randomUUID(), session_id: sessionId, event_type: "navigation", location: { task: task.id, stage: stage.id, step: "review" }, event_timestamp: new Date().toISOString(), data: { direction: final ? "complete_task" : "complete_stage", from_stage: stage.id, to_stage: final ? null : task.stages[stageIndex + 1].id, completed_stages: stageIndex + 1, total_stages: task.stages.length } } }).catch(() => undefined);
    setCompletedStages(stageIndex + 1);
    if (final) { setTaskComplete(true); requestAnimationFrame(() => document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" })); return; }
    setStageIndex((value) => value + 1); setStepIndex(0); setFurthestStep(0); setMastered({});
    requestAnimationFrame(() => document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  const masteredCurrent = mastered[`${stage.id}.${step.id}`];
  const selectStage = (index: number, initialStep = 0) => {
    if (index < 0) { setReviewStageIndex(null); return; }
    if (!progressRestored || (index >= completedStages && index !== stageIndex)) return;
    setReviewInitialStep(initialStep);
    setReviewStageIndex(index < completedStages ? index : null);
    requestAnimationFrame(() => document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  const navigator = <aside className="progress-section" id="learning-path-panel"><div className="progress-heading"><div><p className="eyebrow">Your learning path</p><h1>{task.title}</h1></div><p className="path-count"><strong>{stageIndex + 1}</strong> of 6 stages</p></div><ol className="stage-track"><li className="stage introduction-stage"><Link className="stage-navigation-button" data-stage-navigation href={`/learn/${task.id}`} aria-label="Open task introduction"><span className="stage-node" aria-hidden="true">i</span><span className="stage-copy"><span>Start here</span><strong>Task introduction</strong></span></Link></li><li className="stage dataset-stage"><Link className="stage-navigation-button" data-stage-navigation href={`/learn/${task.id}?view=dataset`} aria-label="Open dataset preview"><span className="stage-node" aria-hidden="true">D</span><span className="stage-copy"><span>Explore</span><strong>Dataset preview</strong></span></Link></li>{task.stages.map((item, index) => <li className={`stage ${index < completedStages ? "complete-stage" : index === stageIndex ? "active" : "locked"} ${(!taskComplete || reviewStageIndex !== null) && (reviewStageIndex ?? stageIndex) === index ? "selected-stage" : ""}`} key={item.id}><button type="button" className="stage-navigation-button" data-stage-navigation disabled={!progressRestored || (index >= completedStages && index !== stageIndex)} aria-current={(!taskComplete || reviewStageIndex !== null) && (reviewStageIndex ?? stageIndex) === index ? "step" : undefined} aria-label={`${index < completedStages ? "Review completed" : "Open"} stage ${index + 1}: ${item.label}`} onClick={() => selectStage(index)}><span className="stage-node">{index < completedStages ? "✓" : index + 1}</span><span className="stage-copy"><span>Stage {index + 1}</span><strong>{item.label}</strong></span></button></li>)}<AssessmentNavigation href={!taskComplete ? `/learn/${task.id}?view=assessment` : undefined} unlocked={progressRestored && taskComplete} selected={taskComplete && reviewStageIndex === null} onClick={() => setReviewStageIndex(null)} /></ol>{reviewStageIndex === null && !taskComplete && <div className="merged-step-bar"><div className="merged-stage-title"><span>Current stage</span><strong>{stage.title}</strong></div><ol className="lesson-steps">{steps.map((item, index) => <li key={item.id}><button disabled={index > furthestStep || taskComplete} className={index === stepIndex ? "lesson-step current" : mastered[`${stage.id}.${item.id}`] ? "lesson-step complete" : "lesson-step locked-step"} onClick={() => moveStep(index)}><span>{index + 1}</span>{item.label}</button></li>)}</ol></div>}</aside>;

  return <LearningShell taskTitle={task.title} overviewHref={`/learn/${task.id}`} navigator={navigator}>
    {reviewStageIndex !== null ? <CompletedStageReview key={`${reviewStageIndex}.${reviewInitialStep}`} task={task.id} stage={taskIntroductions[task.id].stages[reviewStageIndex]} stageNumber={reviewStageIndex + 1} progress={overallProgress} taskComplete={taskComplete} onReturn={() => setReviewStageIndex(null)} completedStages={taskIntroductions[task.id].stages.slice(0, completedStages)} initialStepIndex={reviewInitialStep} onSelectStage={(stageId) => { const index = task.stages.findIndex((item) => item.id === stageId); selectStage(index, index < reviewStageIndex ? steps.length - 1 : 0); }} /> :
    <article className="lesson-content" id="lesson" tabIndex={-1}>
      {progressRestored && completedStages > 0 && <CompletedStagePicker stages={taskIntroductions[task.id].stages.slice(0, completedStages)} onSelect={(stageId) => selectStage(task.stages.findIndex((item) => item.id === stageId))} />}
      {!taskComplete && <header className="lesson-context-header"><div><p className="eyebrow blue">Stage {stageIndex + 1} of {task.stages.length} · {step.label}</p><h2>{stage.title}</h2><p>{stage.intro}</p></div><CircularProgress value={overallProgress} /></header>}
      {!progressRestored && <p className="question-loading">Restoring your saved position…</p>}
      {progressRestored && !taskComplete && <GeneratedTutorCard key={`${stage.id}.${step.id}`} task={task.id} stage={stage.id} step={step.id} actionType={bank[step.id][0].actionType} lessonContext={`${stage.title}. ${stage.intro} Concept: ${stage.concept}. Expected result: ${stage.result}.`} learningObjectives={bank[step.id][0].learningObjectives ?? []} onAttempt={recordAttempt} onPresented={recordPresentation} onRestoredCorrect={(restoredStep) => setMastered((state) => ({ ...state, [`${stage.id}.${restoredStep}`]: true }))} />}
      {taskComplete ? <TaskAssessment task={task.id} onReview={(stageId) => selectStage(task.stages.findIndex((item) => item.id === stageId))} /> : <footer className="lesson-footer"><button className="text-button" disabled={stepIndex === 0 && stageIndex === 0} onClick={() => { if (stepIndex > 0) moveStep(stepIndex - 1); else selectStage(stageIndex - 1, steps.length - 1); }}>← Previous</button><span className={!masteredCurrent ? "progression-note" : ""}>{!masteredCurrent ? "Complete the exercise to continue" : `Step ${stepIndex + 1} of ${steps.length}`}</span>{stepIndex < steps.length - 1 ? <button className="primary-button" disabled={!masteredCurrent} onClick={continueStep}>Continue <span>→</span></button> : <button className="primary-button" disabled={!masteredCurrent} onClick={finishStage}>{stageIndex === task.stages.length - 1 ? "Start final assessment" : "Next stage"} <span>→</span></button>}</footer>}
    </article>}
  </LearningShell>;
}
