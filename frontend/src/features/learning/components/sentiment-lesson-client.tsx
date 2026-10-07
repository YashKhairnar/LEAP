"use client";

import Link from "next/link";
import type { AttemptEvidence } from "@/features/collection/lib/question-exposure";
import { use, useEffect, useState } from "react";
import { questionBanks, sentimentStages, type QuestionItem, type StepId } from "@/features/learning/lib/question-bank";
import { enqueueCollection, flushCollectionQueue, learningSessionId } from "@/features/collection/lib/collection";
import { questionContentId } from "@/features/collection/lib/content-id";
import GeneratedTutorCard from "@/features/learning/components/generated-tutor-card";
import LearningShell from "@/features/learning/components/learning-shell";
import CompletedStageReview from "@/features/learning/components/completed-stage-review";
import CompletedStagePicker from "@/features/learning/components/completed-stage-picker";
import CircularProgress from "@/components/ui/circular-progress";
import TaskAssessment, { AssessmentNavigation } from "@/features/assessment/components/task-assessment";
import { taskIntroductions } from "@/features/learning/lib/lesson-introductions";
import { getAuth, getTaskProgress } from "@/lib/auth";

const lessonSteps: { id: StepId; label: string }[] = [
  { id: "connect", label: "Bridge" },
  { id: "practice", label: "Apply" },
  { id: "review", label: "Check" },
];
const emptyMastery = (): Record<StepId, boolean> => ({ activate: false, connect: false, implement: false, learn: false, practice: false, review: false });

export default function SentimentLesson({ searchParams }: { searchParams: Promise<{ review?: string }> }) {
  const { review: initialReviewStage } = use(searchParams);
  const [stageIndex, setStageIndex] = useState(0);
  const [completedStages, setCompletedStages] = useState(0);
  const [step, setStep] = useState(0);
  const [furthestStep, setFurthestStep] = useState(0);
  const [mastered, setMastered] = useState<Record<StepId, boolean>>(emptyMastery);
  const [confidence, setConfidence] = useState<string | null>(null);
  const [taskComplete, setTaskComplete] = useState(false);
  const [sessionId] = useState(() => typeof window === "undefined" ? "" : learningSessionId());
  const [progressRestored, setProgressRestored] = useState(false);
  const [reviewStageIndex, setReviewStageIndex] = useState<number | null>(null);
  const [reviewInitialStep, setReviewInitialStep] = useState(0);
  const stage = sentimentStages[stageIndex];
  const analogyPreference = getAuth()?.user.analogy_preference ?? "java";
  const useJavaReferences = analogyPreference === "java";
  const useEverydayAnalogies = analogyPreference === "everyday";
  const stageHeading = useJavaReferences ? stage.heading : stage.target;
  const current = lessonSteps[step];
  const overallProgress = taskComplete ? 100 : Math.round(((stageIndex * lessonSteps.length + step) / (sentimentStages.length * lessonSteps.length)) * 100);

  useEffect(() => {
    let active = true;
    void flushCollectionQueue().catch((error) => console.warn("Pending learner events will retry later.", error))
      .then(() => getTaskProgress())
      .then((records) => {
        if (!active) return;
        const saved = records.find((record) => record.task === "sentiment_classification");
        if (saved) {
          const savedStage = sentimentStages.findIndex((item) => item.id === saved.current_stage);
          const restoredStage = savedStage >= 0 ? savedStage : Math.min(saved.completed_stages, sentimentStages.length - 1);
          const savedStep = lessonSteps.findIndex((item) => item.id === saved.current_step);
          const restoredStep = savedStep >= 0 ? savedStep : 0;
          const restoredMastery = emptyMastery();
          lessonSteps.slice(0, restoredStep).forEach((item) => { restoredMastery[item.id] = true; });
          setStageIndex(restoredStage); setStep(restoredStep); setFurthestStep(restoredStep);
          setMastered(restoredMastery); setCompletedStages(saved.completed_stages); setTaskComplete(saved.task_complete);
          const requestedReview = sentimentStages.findIndex((item) => item.id === initialReviewStage);
          if (requestedReview >= 0 && requestedReview < saved.completed_stages) { setReviewInitialStep(0); setReviewStageIndex(requestedReview); }
        }
        setProgressRestored(true);
      }).catch(() => { if (active) setProgressRestored(true); });
    return () => { active = false; };
  }, [initialReviewStage]);

  const recordBehavior = (eventType: "content_presented" | "content_exposure" | "confidence_checkpoint" | "navigation", data: Record<string, unknown>, locationStep = current.id, eventId = crypto.randomUUID()) => {
    void enqueueCollection({ endpoint: "/api/events", payload: {
      event_id: eventId, session_id: sessionId, event_type: eventType,
      location: { task: "sentiment_classification", stage: stage.id, step: locationStep },
      event_timestamp: new Date().toISOString(), data,
    }}).catch((error) => console.warn("Learner event queued for retry.", error));
  };

  const recordPresentation = (item: QuestionItem, presentationId: string) => {
    const contentId = questionContentId("sentiment", item);
    recordBehavior("content_presented", { presentation_id: presentationId, content_id: contentId, action_type: item.actionType, selection_policy: item.selectionPolicy ?? "llm_generated_content_v1", planner_decision: item.plannerDecision, generation_metadata: item.generationMetadata, content: { prompt: item.prompt, options: item.options, correct_answer: item.correctAnswer, explanation: item.explanation, misconception: item.misconception, learning_objectives: item.learningObjectives ?? stage.objectives, lesson_content: item.lessonContent } }, item.step, presentationId);
  };

  const recordAttempt = async (item: QuestionItem, answer: string, correct: boolean, attempt: number, responseTimeMs: number, presentationId: string, evidence: AttemptEvidence) => {
    const stepIndex = lessonSteps.findIndex((lessonStep) => lessonStep.id === item.step);
    const isReview = item.step === "review";
    const decision = correct ? (isReview ? "remain_on_step" : "advance_step") : "remain_on_step";
    const locationAfter = correct
      ? isReview
        ? { task: "sentiment_classification", stage: stage.id, step: "review" }
        : { task: "sentiment_classification", stage: stage.id, step: lessonSteps[stepIndex + 1].id }
      : { task: "sentiment_classification", stage: stage.id, step: item.step };
    const contentId = questionContentId("sentiment", item);
    const transition = {
      transition_id: crypto.randomUUID(), session_id: sessionId,
      location_before: { task: "sentiment_classification", stage: stage.id, step: item.step },
      instructional_action: { action_type: item.actionType, content_id: contentId },
      learner_action: { response: answer },
      observation: { ...evidence, correct, score: correct ? 1 : 0, attempt, response_time_ms: responseTimeMs, misconception: correct ? null : item.misconception },
      progression: { decision }, location_after: locationAfter,
      event_timestamp: new Date().toISOString(), selection_policy: item.selectionPolicy ?? "llm_generated_content_v1", presentation_id: presentationId,
    };
    await enqueueCollection({ endpoint: "/api/interactions", payload: { ...transition, content: item.collectionContent ?? {
      content_id: contentId, task: "sentiment_classification", stage: stage.id, step: item.step,
      action_type: item.actionType, prompt: item.prompt, options: item.options,
      correct_answer: item.correctAnswer, explanation: item.explanation,
      misconception: item.misconception, learning_objectives: item.learningObjectives ?? stage.objectives, lesson_content: item.lessonContent, planner_decision: item.plannerDecision, generation_metadata: item.generationMetadata,
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
    setFurthestStep((value) => Math.max(value, next)); setStep(next);
  };

  const completeStage = () => {
    const finalStage = stageIndex === sentimentStages.length - 1;
    recordBehavior("navigation", { direction: finalStage ? "complete_task" : "complete_stage", from_stage: stage.id, to_stage: finalStage ? null : sentimentStages[stageIndex + 1].id, completed_stages: stageIndex + 1, total_stages: sentimentStages.length });
    setCompletedStages(stageIndex + 1);
    if (finalStage) { setTaskComplete(true); requestAnimationFrame(() => document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" })); return; }
    setStageIndex((value) => value + 1); setStep(0); setFurthestStep(0); setMastered(emptyMastery()); setConfidence(null);
    requestAnimationFrame(() => document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  const selectStage = (index: number, initialStep = 0) => {
    if (index < 0) { setReviewStageIndex(null); return; }
    if (!progressRestored || (index >= completedStages && index !== stageIndex)) return;
    setReviewInitialStep(initialStep);
    setReviewStageIndex(index < completedStages ? index : null);
    requestAnimationFrame(() => document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  const navigator = <aside className="progress-section" aria-labelledby="path-title" id="learning-path-panel"><div className="progress-heading"><div><p className="eyebrow">Your learning path</p><h1 id="path-title">Build a sentiment classifier</h1></div><p className="path-count"><strong>{Math.min(stageIndex + 1, 6)}</strong> of 6 stages</p></div><ol className="stage-track"><li className="stage introduction-stage"><Link className="stage-navigation-button" data-stage-navigation href="/learn/sentiment" aria-label="Open task introduction"><span className="stage-node" aria-hidden="true">i</span><span className="stage-copy"><span>Start here</span><strong>Task introduction</strong></span></Link></li><li className="stage dataset-stage"><Link className="stage-navigation-button" data-stage-navigation href="/learn/sentiment?view=dataset" aria-label="Open dataset preview"><span className="stage-node" aria-hidden="true">D</span><span className="stage-copy"><span>Explore</span><strong>Dataset preview</strong></span></Link></li>{sentimentStages.map((item, index) => <li className={`stage ${index < completedStages ? "complete-stage" : index === stageIndex ? "active" : "locked"} ${(!taskComplete || reviewStageIndex !== null) && (reviewStageIndex ?? stageIndex) === index ? "selected-stage" : ""}`} key={item.id}><button type="button" className="stage-navigation-button" data-stage-navigation disabled={!progressRestored || (index >= completedStages && index !== stageIndex)} aria-current={(!taskComplete || reviewStageIndex !== null) && (reviewStageIndex ?? stageIndex) === index ? "step" : undefined} aria-label={`${index < completedStages ? "Review completed" : "Open"} stage ${index + 1}: ${item.shortLabel}`} onClick={() => selectStage(index)}><span className="stage-node">{index < completedStages ? "✓" : index + 1}</span><span className="stage-copy"><span>Stage {index + 1}</span><strong>{item.shortLabel}</strong></span></button></li>)}<AssessmentNavigation href={!taskComplete ? "/learn/sentiment?view=assessment" : undefined} unlocked={progressRestored && taskComplete} selected={taskComplete && reviewStageIndex === null} onClick={() => setReviewStageIndex(null)} /></ol>{reviewStageIndex === null && !taskComplete && <div className="merged-step-bar"><div className="merged-stage-title"><span>Current stage</span><strong>{stageHeading}</strong></div><ol className="lesson-steps">{lessonSteps.map((item, index) => <li key={item.id}><button disabled={index > furthestStep || taskComplete} className={index === step ? "lesson-step current" : mastered[item.id] ? "lesson-step complete" : index > furthestStep ? "lesson-step locked-step" : "lesson-step"} onClick={() => moveTo(index)}><span>{mastered[item.id] ? <CheckIcon /> : index + 1}</span>{item.label}</button></li>)}</ol><div className="time-estimate"><ClockIcon /> 10–15 min</div></div>}</aside>;

  return <LearningShell taskTitle="Sentiment classification" overviewHref="/learn/sentiment" navigator={navigator}>
    {reviewStageIndex !== null ? <CompletedStageReview key={`${reviewStageIndex}.${reviewInitialStep}`} task="sentiment_classification" stage={taskIntroductions.sentiment.stages[reviewStageIndex]} stageNumber={reviewStageIndex + 1} progress={overallProgress} taskComplete={taskComplete} onReturn={() => setReviewStageIndex(null)} completedStages={taskIntroductions.sentiment.stages.slice(0, completedStages)} initialStepIndex={reviewInitialStep} onSelectStage={(stageId) => { const index = sentimentStages.findIndex((item) => item.id === stageId); selectStage(index, index < reviewStageIndex ? lessonSteps.length - 1 : 0); }} /> :
    <article className="lesson-content" id="lesson" tabIndex={-1}>
      {progressRestored && completedStages > 0 && <CompletedStagePicker stages={taskIntroductions.sentiment.stages.slice(0, completedStages)} onSelect={(stageId) => selectStage(sentimentStages.findIndex((item) => item.id === stageId))} />}
      {!taskComplete && <header className="lesson-context-header"><div><p className="eyebrow blue">Stage {stageIndex + 1} of {sentimentStages.length} · {current.label}</p><h2>{stageHeading}</h2><p>{stage.intro}</p></div><CircularProgress value={overallProgress} /></header>}
      {!progressRestored && <p className="question-loading">Restoring your saved position…</p>}
      {progressRestored && !taskComplete && <GeneratedTutorCard key={`${stage.id}.${current.id}`} task="sentiment_classification" stage={stage.id} step={current.id} actionType={questionBanks[stage.id][current.id][0].actionType} lessonContext={useJavaReferences ? `${stageHeading}. ${stage.intro} Familiar Java concept: ${stage.familiar}. Target ML concept: ${stage.target}. Their relationship: ${stage.relationship}.` : useEverydayAnalogies ? `${stageHeading}. ${stage.intro} Use everyday examples. Target ML concept: ${stage.target}.` : `${stageHeading}. ${stage.intro} Explain the ML concept directly through the Python implementation. Target ML concept: ${stage.target}.`} learningObjectives={stage.objectives} onAttempt={recordAttempt} onPresented={recordPresentation} onRestoredCorrect={(restoredStep) => setMastered((state) => ({ ...state, [restoredStep]: true }))} />}
      {current.id === "review" && mastered.review && !taskComplete && <fieldset className="confidence-check"><legend>How confident are you in this stage?</legend><div>{["Not yet", "Somewhat", "Confident"].map((level) => <button type="button" className={confidence === level ? "confidence selected" : "confidence"} onClick={() => { setConfidence(level); recordBehavior("confidence_checkpoint", { confidence: level, stage: stage.id }); }} key={level}>{level}</button>)}</div></fieldset>}
      {taskComplete && <TaskAssessment task="sentiment_classification" onReview={(stageId) => selectStage(sentimentStages.findIndex((item) => item.id === stageId))} />}
      {!taskComplete && <footer className="lesson-footer"><button className="text-button" disabled={step === 0 && stageIndex === 0} onClick={() => { if (step > 0) moveTo(step - 1); else selectStage(stageIndex - 1, lessonSteps.length - 1); }}>← Previous</button><span className={!mastered[current.id] ? "progression-note" : ""}>{!mastered[current.id] ? "Complete the exercise to continue" : `Step ${step + 1} of ${lessonSteps.length}`}</span>{step < lessonSteps.length - 1 ? <button className="primary-button" disabled={!mastered[current.id]} onClick={continueLesson}>Continue <span>→</span></button> : <button className="primary-button" disabled={!mastered.review || !confidence} onClick={completeStage}>{stageIndex === 5 ? "Start final assessment" : "Next stage"} <span>→</span></button>}</footer>}
    </article>}
  </LearningShell>;
}

function ClockIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>; }
function CheckIcon() { return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 10 3 3 7-7"/></svg>; }
