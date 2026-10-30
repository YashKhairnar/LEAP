"use client";
/* eslint-disable @next/next/no-img-element -- Codapi returns dynamic data-URL plots. */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { API_URL, getAuth } from "@/lib/auth";
import { INSTRUCTIONAL_ACTIONS, type InstructionalActionType, type InstructionalStep } from "@/features/learning/lib/instructional-actions";
import { collectionPlannerDecision, shuffleQuestionOptions, withCollectionContent, type CollectionContent, type QuestionItem } from "@/features/learning/lib/question-bank";
import { enqueueCollection, learningSessionId } from "@/features/collection/lib/collection";
import { questionContentId } from "@/features/collection/lib/content-id";
import { QuestionExposureClock, evidenceKind, type AttemptEvidence } from "@/features/collection/lib/question-exposure";
import { JAVA_ANALOGY_EXAMPLES, stageTerms } from "@/features/learning/lib/learning-support";
import { initialStageScreen } from "@/features/learning/lib/learning-flow";
import DigitMatrixExample from "@/features/learning/components/digit-matrix-example";

type TutorContent = { question: string; options: string[]; expected_answer: string; hint: string; explanation: string; concepts_tested: string[] };
type LessonSectionType = "meaning" | "concept" | "analogy" | "example" | "code" | "result" | "why_it_matters" | "concept_bridge" | "real_life_analogy" | "data_preview" | "pipeline" | "transformation" | "warning" | "metric";
type LessonSection = { type: LessonSectionType; title: string; body: string; items: string[]; code: string | null; language: string | null };
type CodeExperiment = { title: string; find: string; replace: string; expected_change: string };
type LessonContent = { title: string; introduction: string; sections: LessonSection[]; code_explanation?: string[]; try_this?: (CodeExperiment | string)[]; key_takeaway?: string };

export default function GeneratedTutorCard({ task, stage, stageTitle, questionNumber, step, actionType, lessonContext, learningObjectives, onAttempt, onPresented, onRestoredCorrect, onContinue, continueDisabled = false, continueLabel = "Continue", confidence, onConfidence, reviewOnly = false }: {
  task: string; stage: string; stageTitle?: string; questionNumber?: number; step: InstructionalStep; actionType: InstructionalActionType; lessonContext: string; learningObjectives: string[];
  onAttempt: (item: QuestionItem, answer: string, correct: boolean, attempt: number, responseTimeMs: number, presentationId: string, evidence: AttemptEvidence) => Promise<void>;
  onPresented: (item: QuestionItem, presentationId: string) => void;
  onRestoredCorrect?: (step: InstructionalStep) => void;
  onContinue?: () => void;
  continueDisabled?: boolean;
  continueLabel?: string;
  confidence?: string | null;
  onConfidence?: (value: string) => void;
  reviewOnly?: boolean;
}) {
  const learner = getAuth()?.user;
  const lessonKey = `leap.generated.lesson.v20.${learner?.user_id ?? "anonymous"}.${learner?.analogy_preference ?? "java"}.${task}.${stage}`;
  const [stageLesson, setStageLesson] = useState<LessonContent | null>(() => {
    if (typeof window === "undefined" || reviewOnly) return null;
    const saved = window.sessionStorage.getItem(lessonKey);
    if (!saved) return null;
    try { return JSON.parse(saved) as LessonContent; } catch { return null; }
  });
  const [generated, setGenerated] = useState<{ model: string; lesson: LessonContent; content: TutorContent } | null>(null);
  const [item, setItem] = useState<QuestionItem | null>(null);
  const [presentationId, setPresentationId] = useState("");
  const [answer, setAnswer] = useState("");
  const [attempt, setAttempt] = useState(1);
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showHint, setShowHint] = useState(false);
  // Wrong answers on the current question: the first earns a hint, the second reveals the answer.
  const [misses, setMisses] = useState(0);
  const [lessonPartIndex, setLessonPartIndex] = useState(0);
  const toolbarRef = useRef<HTMLDivElement>(null);
  const practiceStartedKey = `leap.practice.started.v1.${learner?.user_id ?? "anonymous"}.${task}.${stage}`;
  const [viewMode, setViewMode] = useState<"learn" | "practice">(() => {
    return initialStageScreen(step, typeof window !== "undefined" && window.sessionStorage.getItem(practiceStartedKey) === "started");
  });
  const practiceNoticeKey = `leap.practice.personalization-notice.v1.${learner?.user_id ?? "anonymous"}.${task}`;
  const [personalizationNoticeAcknowledged, setPersonalizationNoticeAcknowledged] = useState(() => {
    if (typeof window === "undefined" || reviewOnly) return true;
    return window.localStorage.getItem(practiceNoticeKey) === "acknowledged";
  });
  const exposureClock = useRef(new QuestionExposureClock());
  const questionElement = useRef<HTMLDivElement>(null);
  const presented = useRef(new Set<string>());
  const hintUsed = useRef(false);
  const answerRevealed = useRef(false);
  const historyKnown = useRef(true);
  const prefetched = useRef(new Set<string>());
  const onAttemptRef = useRef(onAttempt);
  const onPresentedRef = useRef(onPresented);
  const onRestoredCorrectRef = useRef(onRestoredCorrect);
  const changeViewMode = (mode: "learn" | "practice") => {
    setViewMode(mode);
    if (mode === "practice") window.sessionStorage.setItem(practiceStartedKey, "started");
    requestAnimationFrame(() => {
      const chips = toolbarRef.current;
      if (!chips) return;
      chips.focus({ preventScroll: true });
      // Keep the step chips visible below the sticky header.
      const top = chips.getBoundingClientRect().top + window.scrollY - 92;
      if (window.scrollY > top) window.scrollTo({ top, behavior: "smooth" });
    });
  };
  useEffect(() => { onAttemptRef.current = onAttempt; onPresentedRef.current = onPresented; onRestoredCorrectRef.current = onRestoredCorrect; }, [onAttempt, onPresented, onRestoredCorrect]);

  const prefetchNextStep = useCallback(async (lesson: LessonContent) => {
    const nextStep: InstructionalStep | null = step === "connect" ? "practice" : step === "practice" ? "review" : null;
    if (reviewOnly || !nextStep) return;
    const cacheKey = `${task}.${stage}.${nextStep}`;
    if (prefetched.current.has(cacheKey)) return;
    prefetched.current.add(cacheKey);
    try {
      const candidates = INSTRUCTIONAL_ACTIONS[nextStep].map((candidateAction) => ({
        action_type: candidateAction,
        prompt: `${candidateAction}: ${lessonContext}`,
      }));
      const planResponse = await fetch(`${API_URL}/api/tutor/plan`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: window.sessionStorage.getItem("leap.learning.session.v1"), task, stage, step: nextStep, candidates }),
      });
      const plan = await planResponse.json() as Record<string, unknown> & { selected_action_type?: InstructionalActionType };
      if (!planResponse.ok || !plan.selected_action_type) throw new Error(plan.detail ? String(plan.detail) : `Prefetch planner returned ${planResponse.status}`);
      const generationResponse = await fetch(`${API_URL}/api/tutor/generate`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task, stage, step: nextStep, action_type: plan.selected_action_type,
          reference_prompt: lessonContext, learning_objectives: learningObjectives,
          existing_lesson: lesson, planner_decision: collectionPlannerDecision(plan),
        }),
      });
      if (!generationResponse.ok) throw new Error(`Prefetch generation returned ${generationResponse.status}`);
    } catch (reason) {
      prefetched.current.delete(cacheKey);
      console.warn("Next tutor content prefetch failed; it will generate on demand.", reason);
    }
  }, [learningObjectives, lessonContext, reviewOnly, stage, step, task]);

  const requestContent = useCallback(async (selectedAction: InstructionalActionType = actionType, plannerDecision?: Record<string, unknown>, resumeExisting = false) => {
    try {
      if (resumeExisting || reviewOnly) {
        const resumeResponse = await fetch(`${API_URL}/api/tutor/resume/${encodeURIComponent(task)}/${encodeURIComponent(stage)}/${encodeURIComponent(step)}${reviewOnly ? "?review=true" : ""}`, { credentials: "include", cache: "no-store" });
        const resumed = await resumeResponse.json() as {
          detail?: string;
          lesson?: LessonContent | null;
          active_question?: { content_instance_id: string; model: string; prompt_version: string; code_version: string; dataset: Record<string, unknown>; lesson: LessonContent; content: TutorContent; collection_content?: CollectionContent } | null;
          action_type?: InstructionalActionType | null;
          question_state?: { presentation_id?: string | null; answer?: string | null; correct?: boolean | null; attempt: number; hint_used?: boolean } | null;
        };
        if (!resumeResponse.ok) throw new Error(resumed.detail ?? `Resume API returned ${resumeResponse.status}`);
        if (resumed.lesson) {
          if (!reviewOnly) window.sessionStorage.setItem(lessonKey, JSON.stringify(resumed.lesson));
          setStageLesson(resumed.lesson);
        }
        if (resumed.active_question) {
          const saved = resumed.active_question;
          const restoredAction = resumed.action_type ?? selectedAction;
          const restoredItem: QuestionItem = {
            id: `generated.${saved.content_instance_id}`, step, actionType: restoredAction,
            typeLabel: "LLM-generated question", prompt: saved.content.question,
            options: shuffleQuestionOptions(`generated.${saved.content_instance_id}`, saved.content.options, saved.content.expected_answer), correctAnswer: saved.content.expected_answer,
            explanation: saved.content.explanation, misconception: "generated_question_incorrect",
            learningObjectives: saved.content.concepts_tested.length ? saved.content.concepts_tested : learningObjectives,
            lessonContent: saved.lesson, selectionPolicy: "legacy_unknown",
            generationMetadata: { schema_version: "stage_sections_question_v3", prompt_version: saved.prompt_version, code_version: saved.code_version, curriculum_layout: "six_part_explorable_lesson_v2", model: saved.model, dataset: saved.dataset, task, stage, step, selected_action_type: restoredAction, content_instance_id: saved.content_instance_id, resumed: true },
          };
          const restoredState = resumed.question_state;
          setGenerated({ model: saved.model, lesson: saved.lesson, content: saved.content });
          setItem(withCollectionContent(restoredItem, saved.collection_content));
          setPresentationId(crypto.randomUUID());
          hintUsed.current = restoredState?.hint_used ?? false;
          answerRevealed.current = restoredState?.correct !== null && restoredState?.correct !== undefined;
          historyKnown.current = false; // A previous tab may have unsynced assistance events.
          setAnswer(restoredState?.answer ?? "");
          setAttempt(restoredState?.attempt ?? 1);
          setChecked(restoredState?.correct !== null && restoredState?.correct !== undefined);
          setMisses(restoredState?.correct === false ? Math.min(2, restoredState.attempt) : 0);
          setStageLesson(saved.lesson);
          if (restoredState?.correct) onRestoredCorrectRef.current?.(step);
          void prefetchNextStep(saved.lesson);
          return;
        }
      }
      if (reviewOnly) return;
      let effectiveAction = selectedAction;
      let effectiveDecision = plannerDecision;
      if (!effectiveDecision) {
        const candidates = INSTRUCTIONAL_ACTIONS[step].map((candidateAction) => ({ action_type: candidateAction, prompt: `${candidateAction}: ${lessonContext}` }));
        const planResponse = await fetch(`${API_URL}/api/tutor/plan`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: window.sessionStorage.getItem("leap.learning.session.v1"), task, stage, step, candidates }) });
        const planned = await planResponse.json() as Record<string, unknown> & { detail?: string; selected_action_type?: InstructionalActionType };
        if (!planResponse.ok || !planned.selected_action_type) throw new Error(planned.detail ?? `Planner API returned ${planResponse.status}`);
        effectiveAction = planned.selected_action_type;
        effectiveDecision = planned;
      }
      effectiveDecision = collectionPlannerDecision(effectiveDecision) ?? undefined;
      const cachedLessonRaw = window.sessionStorage.getItem(lessonKey);
      let cachedLesson: LessonContent | null = null;
      if (cachedLessonRaw) {
        try { cachedLesson = JSON.parse(cachedLessonRaw) as LessonContent; } catch { window.sessionStorage.removeItem(lessonKey); }
      }
      const response = await fetch(`${API_URL}/api/tutor/generate`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task, stage, step, action_type: effectiveAction, reference_prompt: lessonContext, learning_objectives: learningObjectives, existing_lesson: cachedLesson, planner_decision: effectiveDecision }) });
      const body = await response.json() as { detail?: string; content_instance_id?: string; model?: string; prompt_version?: string; code_version?: string; dataset?: Record<string, unknown>; lesson?: LessonContent; content?: TutorContent; collection_content?: CollectionContent };
      if (!response.ok || !body.content_instance_id || !body.model || !body.prompt_version || !body.code_version || !body.lesson || !body.content) throw new Error(body.detail ?? `Tutor API returned ${response.status}`);
      const content = body.content;
      if (!cachedLesson) window.sessionStorage.setItem(lessonKey, JSON.stringify(body.lesson));
      setStageLesson(body.lesson);
      const assignmentPolicy = typeof effectiveDecision?.assignment_policy === "string" ? effectiveDecision.assignment_policy : "uniform_random_v1";
      const nextItem: QuestionItem = { id: `generated.${body.content_instance_id}`, step, actionType: effectiveAction, typeLabel: "Authored question", prompt: content.question, options: shuffleQuestionOptions(`generated.${body.content_instance_id}`, content.options, content.expected_answer), correctAnswer: content.expected_answer, explanation: content.explanation, misconception: "generated_question_incorrect", learningObjectives: content.concepts_tested.length ? content.concepts_tested : learningObjectives, lessonContent: body.lesson, plannerDecision: effectiveDecision, selectionPolicy: assignmentPolicy, generationMetadata: { schema_version: "stage_sections_question_v3", prompt_version: body.prompt_version, code_version: body.code_version, curriculum_layout: "stage_sections_question_v3", model: body.model, dataset: body.dataset, task, stage, step, selected_action_type: effectiveAction, assignment_policy: assignmentPolicy, selection_probability: effectiveDecision?.selection_probability, content_instance_id: body.content_instance_id, curriculum_context: lessonContext, requested_learning_objectives: learningObjectives, lesson_reused: cachedLesson !== null, generated_at: new Date().toISOString() } };
      const nextPresentationId = crypto.randomUUID();
      setGenerated({ model: body.model, lesson: body.lesson, content }); setItem(withCollectionContent(nextItem, body.collection_content)); setPresentationId(nextPresentationId);
      setAttempt(1); setMisses(0); hintUsed.current = false; answerRevealed.current = false; historyKnown.current = true;
      void prefetchNextStep(body.lesson);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The tutor could not generate content."); }
    finally { setLoading(false); }
  }, [actionType, learningObjectives, lessonContext, lessonKey, prefetchNextStep, stage, step, task, reviewOnly]);

  useEffect(() => {
    const requestTimer = window.setTimeout(() => void requestContent(actionType, undefined, true), 0);
    return () => window.clearTimeout(requestTimer);
  }, [actionType, requestContent]);

  const regenerate = () => {
    if (reviewOnly) { setLoading(true); setError(""); void requestContent(actionType, undefined, true); return; }
    setAttempt((value) => value + 1); setLoading(true); setError("");
    setItem(null); setAnswer(""); setChecked(false); setShowHint(false); void requestContent();
  };

  const tryAnotherAfterIncorrect = async () => {
    setLoading(true); setError(""); setShowHint(false);
    try {
      const candidates = INSTRUCTIONAL_ACTIONS[step].map((candidateAction) => ({ action_type: candidateAction, prompt: `${candidateAction}: ${lessonContext}` }));
      const response = await fetch(`${API_URL}/api/tutor/plan`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: window.sessionStorage.getItem("leap.learning.session.v1"), task, stage, step, candidates }) });
      const decision = await response.json() as Record<string, unknown> & { detail?: string; selected_action_type?: InstructionalActionType };
      if (!response.ok || !decision.selected_action_type) throw new Error(decision.detail ?? `Planner API returned ${response.status}`);
      setAttempt((value) => value + 1);
      setItem(null); setAnswer(""); setChecked(false);
      await requestContent(decision.selected_action_type, decision);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The planner could not select the next action."); setLoading(false);
    }
  };

  const check = async (now: number) => {
    if (reviewOnly || !item || !answer.trim() || checked) return;
    const correct = normalize(answer) === normalize(item.correctAnswer);
    const duration = exposureClock.current.elapsed(now);
    exposureClock.current.setVisible(false, now);
    const evidence: AttemptEvidence = { hint_used: hintUsed.current, answer_revealed_before_attempt: answerRevealed.current,
      evidence_kind: evidenceKind(hintUsed.current, answerRevealed.current, historyKnown.current),
      timing_version: "visible_foreground_v1", exposure_id: presentationId };
    setChecked(true);
    const revealsAnswer = correct || misses + 1 >= 2;
    if (!correct) setMisses((value) => value + 1);
    const saving = onAttemptRef.current(item, answer, correct, attempt, duration, presentationId, evidence);
    if (revealsAnswer) {
      answerRevealed.current = true;
      recordExposure("answer_revealed");
    } else {
      // The first miss shows the hint instead of the answer.
      hintUsed.current = true;
      recordExposure("hint_shown_after_incorrect");
    }
    await saving;
  };

  const retryCurrentQuestion = () => {
    setAnswer("");
    setChecked(false);
    setShowHint(false);
    setAttempt((value) => value + 1);
    setPresentationId(crypto.randomUUID());
  };

  const recordExposure = (kind: string) => {
    if (!item || reviewOnly) return;
    void enqueueCollection({ endpoint: "/api/events", payload: {
      event_id: crypto.randomUUID(), session_id: learningSessionId(), event_type: "content_exposure",
      location: { task, stage, step }, event_timestamp: new Date().toISOString(),
      data: { kind, content_id: questionContentId(task, item), content_instance_id: item.generationMetadata?.content_instance_id,
        presentation_id: presentationId, attempt, timing_version: "visible_foreground_v1" },
    }}).catch(() => undefined);
  };

  useEffect(() => {
    exposureClock.current.reset();
  }, [presentationId]);

  useEffect(() => {
    const element = questionElement.current;
    if (!item || !element || !presentationId || reviewOnly || loading || checked) return;
    const clock = exposureClock.current;
    let intersecting = false;
    let visible = false;
    const update = () => {
      const next = intersecting && document.visibilityState === "visible";
      if (next === visible) return;
      visible = next;
      clock.setVisible(next, performance.now());
      if (next && !presented.current.has(presentationId)) {
        presented.current.add(presentationId);
        onPresentedRef.current(item, presentationId);
      }
      void enqueueCollection({ endpoint: "/api/events", payload: {
        event_id: crypto.randomUUID(), session_id: learningSessionId(), event_type: "content_exposure",
        location: { task, stage, step }, event_timestamp: new Date().toISOString(),
        data: { kind: next ? "question_visible" : "question_hidden", content_id: questionContentId(task, item),
          content_instance_id: item.generationMetadata?.content_instance_id, presentation_id: presentationId,
          active_time_ms: clock.elapsed(performance.now()), timing_version: "visible_foreground_v1" },
      }}).catch(() => undefined);
    };
    const observer = new IntersectionObserver(([entry]) => { intersecting = entry.isIntersecting; update(); }, { threshold: 0 });
    observer.observe(element);
    document.addEventListener("visibilitychange", update);
    return () => { observer.disconnect(); document.removeEventListener("visibilitychange", update); intersecting = false; update(); };
  }, [item, presentationId, viewMode, checked, loading, reviewOnly, task, stage, step, personalizationNoticeAcknowledged]);

  const correct = item ? normalize(answer) === normalize(item.correctAnswer) : false;
  const showPersonalizationNotice = Boolean(generated && item && !reviewOnly && !checked && !personalizationNoticeAcknowledged);

  const acknowledgePersonalizationNotice = () => {
    window.localStorage.setItem(practiceNoticeKey, "acknowledged");
    setPersonalizationNoticeAcknowledged(true);
  };

  const ideaSections = stageLesson?.sections.filter((section) => section.type !== "code" && section.type !== "result") ?? [];
  const codeSection = stageLesson?.sections.find((section) => section.type === "code") ?? null;
  const resultSection = stageLesson?.sections.find((section) => section.type === "result") ?? null;
  const hasExperiments = Boolean(codeSection && stageLesson?.try_this?.some((suggestion) => typeof suggestion !== "string"));
  const lessonParts: LessonPart[] = ["idea", ...(codeSection ? ["code" as const] : []), ...(hasExperiments ? ["try" as const] : [])];
  const currentPart = lessonParts[Math.min(lessonPartIndex, lessonParts.length - 1)] ?? "idea";
  const isLastPart = lessonPartIndex >= lessonParts.length - 1;
  const revealed = checked && (correct || misses >= 2);
  const goToPart = (index: number) => { setLessonPartIndex(index); changeViewMode("learn"); };

  return <section className="generated-tutor-card" aria-live="polite">
    {stageLesson && <nav className="stage-step-chips" aria-label="Steps in this stage" ref={toolbarRef} tabIndex={-1}>
      <ol>
        {lessonParts.map((part, index) => {
          const current = viewMode === "learn" && currentPart === part;
          const done = viewMode === "practice" || index < lessonPartIndex;
          return <li key={part}><button type="button" className={current ? "current" : done ? "done" : ""} aria-current={current ? "step" : undefined} onClick={() => goToPart(index)}>
            <span aria-hidden="true">{done && !current ? <CheckIcon /> : index + 1}</span>{LESSON_PART_LABELS[part]}
          </button></li>;
        })}
        <li><button type="button" className={viewMode === "practice" ? "current" : ""} aria-current={viewMode === "practice" ? "step" : undefined} onClick={() => changeViewMode("practice")}>
          <span aria-hidden="true">{lessonParts.length + 1}</span>Check{questionNumber ? ` · ${questionNumber} of 3` : ""}
        </button></li>
      </ol>
    </nav>}

    {!stageLesson && loading && (
      <div className="card-loading-state">
        <div className="loading-pulse-line" />
        <p>{reviewOnly ? "Loading your saved lesson…" : "Loading your lesson…"}</p>
      </div>
    )}

    {!stageLesson && error && (
      <div className="card-error-state">
        <p className="generated-tutor-error">{reviewOnly ? "This saved lesson isn’t available right now." : "The lesson didn’t load."} {error}</p>
        <button className="alternate-button" onClick={regenerate}>Try again</button>
      </div>
    )}

    {reviewOnly && !stageLesson && !loading && !error && <p className="question-loading">No saved lesson is available for this stage yet.</p>}

    {stageLesson && (
      <div className={`generated-learning-workspace mode-${viewMode}`}>
        {viewMode === "learn" && (
          <article className="generated-lesson-pane">
            {currentPart === "idea" && <>
              <h2 className="lesson-part-title">{stageLesson.title || stageTitle}</h2>
              <div className="idea-sections">
                {ideaSections.map((section, index) => <IdeaSection section={section} task={task} stage={stage} step={step} key={`${section.type}.${index}`} />)}
              </div>
              <details className="words-to-know">
                <summary>Words to know</summary>
                <p>{stageTerms(task, stage)}</p>
              </details>
            </>}

            {currentPart === "code" && codeSection && <>
              <h2 className="lesson-part-title">Run the code</h2>
              {resultSection && <p className="lesson-part-intro"><strong>What it produces:</strong> {resultSection.body}</p>}
              <ExecutableLessonCell section={codeSection} task={task} stage={stage} step={step} codeExplanation={stageLesson.code_explanation ?? []} tryThis={[]} />
            </>}

            {currentPart === "try" && codeSection && <>
              <h2 className="lesson-part-title">Try a change</h2>
              <p className="lesson-part-intro">Make one small edit, run the code again, and see what changes.</p>
              <ExecutableLessonCell section={codeSection} task={task} stage={stage} step={step} codeExplanation={[]} tryThis={stageLesson.try_this ?? []} showInstruction={false} />
            </>}

            {isLastPart && stageLesson.key_takeaway && <p className="key-takeaway"><strong>Remember:</strong> {stageLesson.key_takeaway}</p>}

            <div className="lesson-part-nav">
              {lessonPartIndex > 0 ? <button type="button" className="text-button" onClick={() => goToPart(lessonPartIndex - 1)}>← Back</button> : <span />}
              {isLastPart
                ? <button type="button" className="primary-button" onClick={() => changeViewMode("practice")}>{reviewOnly ? "View saved questions" : "Next: check your understanding"} <span aria-hidden="true">→</span></button>
                : <button type="button" className="primary-button" onClick={() => goToPart(lessonPartIndex + 1)}>{lessonParts[lessonPartIndex + 1] === "code" ? "Next: see the code" : "Next: try a change"} <span aria-hidden="true">→</span></button>}
            </div>
          </article>
        )}

        {viewMode === "practice" && (
          <div className="generated-question-pane">
            <p className="practice-meta">Practice · doesn’t count toward your score</p>

            {loading && <p className="question-loading">{reviewOnly ? "Loading your saved question…" : "Preparing your question…"}</p>}

            {error && (
              <div className="card-error-state">
                <p className="generated-tutor-error">The question didn’t load. {error}</p>
                <button className="alternate-button" onClick={regenerate}>Try again</button>
              </div>
            )}

            {reviewOnly && !loading && !error && !item && <p className="question-loading">No saved question is available for this step.</p>}

            {showPersonalizationNotice && (
              <section className="practice-personalization-notice" aria-labelledby="practice-personalization-title">
                <span className="practice-notice-label">Before your first practice question</span>
                <h3 id="practice-personalization-title">A quick note about practice</h3>
                <p>Your answers help us see which ideas are clear and which may need another explanation. We record:</p>
                <ul>
                  <li>Your answer and whether it was correct</li>
                  <li>Your attempt count and whether you opened a hint</li>
                  <li>Your active response time while the question is visible</li>
                </ul>
                <p>Question styles are currently chosen at random. Your responses are collected for research. Practice is separate from the final assessment score.</p>
                <div className="practice-notice-actions">
                  <button className="primary-button" type="button" onClick={acknowledgePersonalizationNotice}>I understand — start practice</button>
                  <Link href="/privacy" target="_blank">Read the data notice</Link>
                </div>
              </section>
            )}

            {generated && item && !showPersonalizationNotice && (
              <div ref={questionElement} className="practice-question">
                <h3 className="generated-question">{item.prompt}</h3>

                <div className="answers-grid">
                  {item.options.map((option, index) => {
                    const letter = ["A", "B", "C", "D"][index] ?? String.fromCharCode(65 + index);
                    const isSelected = answer === option;
                    let optionStatusClass = "";
                    if (checked) {
                      if (isSelected) optionStatusClass = correct ? "answer-correct-chosen" : "answer-incorrect-chosen";
                      else if (revealed && option === item.correctAnswer) optionStatusClass = "answer-revealed-correct";
                      else if (revealed) optionStatusClass = "answer-dimmed";
                    } else if (isSelected) {
                      optionStatusClass = "selected";
                    }
                    return (
                      <button type="button" disabled={checked || reviewOnly} aria-pressed={isSelected} className={`answer-card ${optionStatusClass}`} onClick={() => setAnswer(option)} key={option}>
                        <span className="answer-letter">{letter}</span>
                        <span className="answer-text">{option}</span>
                        {checked && revealed && option === item.correctAnswer && <span className="status-badge correct-badge">Correct</span>}
                        {checked && isSelected && !correct && <span className="status-badge incorrect-badge">Not quite</span>}
                      </button>
                    );
                  })}
                </div>

                {!checked && !reviewOnly && (
                  <div className="generated-tutor-actions">
                    <button type="button" className="text-button hint-link" onClick={() => { if (!showHint) { hintUsed.current = true; recordExposure("hint_opened"); } setShowHint((value) => !value); }}>
                      {showHint ? "Hide hint" : "Show a hint"}
                    </button>
                    <button type="button" className="primary-button" disabled={!answer.trim()} onClick={() => void check(performance.now())}>Check answer</button>
                  </div>
                )}

                {showHint && !checked && <p className="hint-card"><strong>Hint:</strong> {generated.content.hint}</p>}

                {checked && correct && (
                  <div className="feedback-card feedback-correct">
                    <strong>Correct. Why this works:</strong>
                    <p>{item.explanation}</p>
                  </div>
                )}

                {checked && !correct && !revealed && (
                  <div className="feedback-card feedback-nudge">
                    <strong>Not quite. Here’s a nudge.</strong>
                    <p>{generated.content.hint || "Look back at the main idea of this stage, then try again."}</p>
                    {!reviewOnly && <button className="primary-button" type="button" onClick={retryCurrentQuestion}>Try again</button>}
                  </div>
                )}

                {checked && !correct && revealed && (
                  <div className="feedback-card feedback-incorrect">
                    <strong>Not quite. The answer is “{item.correctAnswer}”.</strong>
                    <p>{item.explanation}</p>
                    {!reviewOnly && <div className="feedback-actions">
                      <button className="primary-button" type="button" onClick={retryCurrentQuestion}>Choose the answer</button>
                      <button className="text-button" type="button" disabled={loading} onClick={() => void tryAnotherAfterIncorrect()}>{loading ? "Preparing…" : "Try a similar question instead"}</button>
                    </div>}
                  </div>
                )}

                {step === "review" && onConfidence && !reviewOnly && checked && correct && (
                  <fieldset className="confidence-check confidence-check-inline">
                    <legend>How sure do you feel about this stage?</legend>
                    <div>{["Not yet", "Somewhat", "Confident"].map((level) => <button type="button" aria-pressed={confidence === level} className={confidence === level ? "confidence selected" : "confidence"} onClick={() => onConfidence(level)} key={level}>{level}</button>)}</div>
                  </fieldset>
                )}

                {onContinue && !reviewOnly && checked && correct && (
                  <div className="question-continue">
                    {continueDisabled && <span role="status">Choose how sure you feel to continue.</span>}
                    <button type="button" className="primary-button" disabled={continueDisabled} onClick={onContinue}>{continueLabel === "Continue" ? "Next question" : continueLabel} <span aria-hidden="true">→</span></button>
                  </div>
                )}
              </div>
            )}

            <div className="lesson-part-nav">
              <button type="button" className="text-button" onClick={() => goToPart(lessonParts.length - 1)}>← Back to the lesson</button>
            </div>
          </div>
        )}
      </div>
    )}
  </section>;
}

type LessonPart = "idea" | "code" | "try";
const LESSON_PART_LABELS: Record<LessonPart, string> = { idea: "Idea", code: "Code", try: "Try it" };
function CheckIcon() { return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 10 3 3 7-7" /></svg>; }

function normalize(value: string): string { return value.trim().toLocaleLowerCase(); }

function repeatsCode(body: string, code: string | null): boolean {
  if (!code) return false;
  const compact = (value: string) => value.toLocaleLowerCase().replace(/[\s`]+/g, "").replace(/;+/g, "");
  const compactBody = compact(body);
  const compactCode = compact(code);
  return compactBody === compactCode || compactBody.includes(compactCode);
}

// The Idea step gives each kind of section its own visual role; older section types fall back to the plain view.
function IdeaSection({ section, task, stage, step }: { section: LessonSection; task: string; stage: string; step: InstructionalStep }) {
  const preference = getAuth()?.user?.analogy_preference;
  if (section.type === "meaning") return <section className="idea-intro">
    <p className="idea-lead">{section.body}</p>
    {section.items.length > 0 && <div className="idea-goals">
      <h3>In this stage you’ll</h3>
      <ol>{section.items.map((item, index) => <li key={item}><span aria-hidden="true">{index + 1}</span>{item}</li>)}</ol>
    </div>}
  </section>;
  if (section.type === "analogy" || section.type === "concept" || section.type === "real_life_analogy") {
    const javaExample = preference === "java" && section.type === "analogy" ? JAVA_ANALOGY_EXAMPLES[`${task}.${stage}`] : undefined;
    const label = section.type === "concept" ? "In machine learning terms" : preference === "java" ? "If you know Java" : "Think of it like this";
    return <section className="idea-card idea-card-analogy">
      <h3><LightbulbIcon />{label}</h3>
      <p>{section.body}</p>
      {javaExample && <figure className="idea-java">
        <pre><code>{javaExample.code}</code></pre>
        <figcaption>{javaExample.explanation}</figcaption>
      </figure>}
    </section>;
  }
  if (section.type === "example") {
    // Items written as "a | b | c" become table rows (a leading "# " row names the columns); anything else is a caption.
    const header = section.items[0]?.startsWith("# ") ? section.items[0].slice(2).split(" | ") : ["Column", "Value", "What it is"];
    const body = section.items.filter((item) => !item.startsWith("# "));
    const rows = body.filter((item) => item.split(" | ").length === 3).map((item) => item.split(" | "));
    const notes = body.filter((item) => item.split(" | ").length !== 3);
    return <section className="idea-card idea-card-example">
      <h3><TableIcon />Worked example</h3>
      <p>{section.body}</p>
      {rows.length > 0 && <div className="idea-example-table"><table>
        <thead><tr>{header.map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead>
        <tbody>{rows.map(([column, value, role]) => <tr key={column}><th scope="row"><code>{column}</code></th><td>{value}</td><td>{role}</td></tr>)}</tbody>
      </table></div>}
      {notes.map((note) => <p className="idea-example-note" key={note}>{note}</p>)}
      {task === "cnn" && stage === "load_images" && <DigitMatrixExample />}
    </section>;
  }
  if (section.type === "why_it_matters") return <section className="idea-card idea-card-why">
    <h3><AlertIcon />Why it matters</h3>
    <p>{section.body}</p>
  </section>;
  return <LessonSectionView section={section} task={task} stage={stage} step={step} />;
}

function LightbulbIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18h6m-5 3h4M8 14a6 6 0 1 1 8 0c-1 1-1 2-1 2H9s0-1-1-2Z" /></svg>; }
function TableIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 10h18M9 10v10" /></svg>; }
function AlertIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 9v4m0 4h.01M10.3 3.9 2.4 17.5A2 2 0 0 0 4.1 20.5h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /></svg>; }

function LessonSectionView({ section, task, stage, step, codeExplanation = [], tryThis = [] }: { section: LessonSection; task: string; stage: string; step: InstructionalStep; codeExplanation?: string[]; tryThis?: (CodeExperiment | string)[] }) {
  const isOrderedList = section.type === "pipeline" || section.type === "transformation";
  const showJavaExample = section.type === "analogy" && getAuth()?.user?.analogy_preference === "java";
  const javaExample = JAVA_ANALOGY_EXAMPLES[`${task}.${stage}`];

  return (
    <section className={`lesson-section lesson-section-${section.type}`}>
      <h4 className="section-title">
        {section.type === "analogy" && <svg className="lesson-highlight-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18h6m-5 3h4M8 14a6 6 0 1 1 8 0c-1 1-1 2-1 2H9s0-1-1-2Z" /></svg>}
        {sectionLabel(section.type)}
      </h4>
      {section.type === "code" ? (
        <ExecutableLessonCell section={section} task={task} stage={stage} step={step} codeExplanation={codeExplanation} tryThis={tryThis} />
      ) : (
        <p className="section-body">{section.body}</p>
      )}
      {showJavaExample && javaExample && (
        <div className="java-analogy-example">
          <strong>Small Java example</strong>
          <pre><code>{javaExample.code}</code></pre>
          <p>{javaExample.explanation}</p>
        </div>
      )}
      
      {section.type !== "code" && section.type !== "why_it_matters" && section.items.length > 0 && (
        <>
        {isOrderedList ? (
          <ol className="section-bullet-list">
            {section.items.map((item) => <li key={item}>{item}</li>)}
          </ol>
        ) : (
          <ul className="section-bullet-list">
            {section.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
        </>
      )}
      {section.type === "data_preview" && <DatasetLessonPreview task={task} />}
    </section>
  );
}

type DatasetInfo = { dataset_id: string; version: string; runtime_filename: string; target: string; columns: string[]; row_count: number; preview: Record<string, string>[] };
type ExecutionResult = { success: boolean; stdout: string; stderr: string; result: unknown; table_preview: { columns: string[]; rows: Record<string, unknown>[] } | null; plots: string[]; duration_ms: number; replayed_cells: number; dataset: DatasetInfo };

function DatasetLessonPreview({ task }: { task: string }) {
  const [dataset, setDataset] = useState<DatasetInfo | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void fetch(`${API_URL}/api/datasets/${task}`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Dataset API returned ${response.status}`);
        return response.json() as Promise<DatasetInfo>;
      })
      .then((value) => { if (active) setDataset(value); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [task]);

  if (failed) return <p className="dataset-preview-status" role="status">The dataset preview is temporarily unavailable.</p>;
  if (!dataset) return <div className="dataset-preview-skeleton" aria-label="Loading dataset preview" />;

  return <div className="lesson-dataset-preview">
    <div className="lesson-dataset-meta"><span>{dataset.runtime_filename}</span><span>{dataset.row_count} rows · Target: {dataset.target}</span></div>
    <DataTable columns={dataset.columns} rows={dataset.preview} />
  </div>;
}

function ExecutableLessonCell({ section, task, stage, step, codeExplanation, tryThis, showInstruction = true }: { section: LessonSection; task: string; stage: string; step: InstructionalStep; codeExplanation: string[]; tryThis: (CodeExperiment | string)[]; showInstruction?: boolean }) {
  const editorKey = `leap.code.v1.${task}.${stage}`;
  const [code, setCode] = useState(() => typeof window === "undefined" ? section.code ?? "" : window.sessionStorage.getItem(editorKey) ?? section.code ?? "");
  const [dataset, setDataset] = useState<DatasetInfo | null>(null);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [running, setRunning] = useState(false);
  const [copied, setCopied] = useState(false);
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const [appliedExperiment, setAppliedExperiment] = useState<number | null>(null);
  const [editStatus, setEditStatus] = useState("");
  const experiments = tryThis.filter((suggestion): suggestion is CodeExperiment => typeof suggestion !== "string");
  const instruction = repeatsCode(section.body, section.code)
    ? "Run the code, then check that the output matches what this step describes."
    : section.body;

  useEffect(() => {
    void fetch(`${API_URL}/api/datasets/${task}`, { credentials: "include" })
      .then(async (response) => { if (!response.ok) throw new Error(`Dataset API returned ${response.status}`); return response.json() as Promise<DatasetInfo>; })
      .then(setDataset).catch(() => setDataset(null));
  }, [task]);

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API is restricted
    }
  };

  const resetCode = () => {
    const original = section.code ?? "";
    setCode(original);
    setResult(null);
    setAppliedExperiment(null);
    setEditStatus("Original code restored. Choose an experiment or run the code.");
    window.sessionStorage.setItem(editorKey, original);
  };

  const applyExperiment = (experiment: CodeExperiment, index: number) => {
    const start = code.indexOf(experiment.find);
    if (running || appliedExperiment !== null || !experiment.find || start < 0 || start !== code.lastIndexOf(experiment.find)) return;
    const updated = code.slice(0, start) + experiment.replace + code.slice(start + experiment.find.length);
    setCode(updated);
    setResult(null);
    setAppliedExperiment(index);
    setEditStatus(`Applied: ${experiment.title}. The changed code is selected. Run code to see the result.`);
    window.sessionStorage.setItem(editorKey, updated);
    requestAnimationFrame(() => {
      editorRef.current?.focus({ preventScroll: true });
      editorRef.current?.setSelectionRange(start, start + experiment.replace.length);
      editorRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
    });
  };

  const run = async () => {
    setRunning(true); setResult(null); setEditStatus(""); window.sessionStorage.setItem(editorKey, code);
    try {
      let response: Response | null = null;
      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          response = await fetch(`${API_URL}/api/code/run`, {
            method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ execution_id: crypto.randomUUID(), session_id: window.sessionStorage.getItem("leap.learning.session.v1"), task, stage, step, code }),
          });
        } catch (reason) {
          if (attempt === 0) {
            setEditStatus("The runtime is waking up. Retrying once…");
            await new Promise((resolve) => window.setTimeout(resolve, 700));
            continue;
          }
          throw reason;
        }
        if (response.status < 500 || attempt === 1) break;
        setEditStatus("The runtime returned a temporary error. Retrying once…");
        await new Promise((resolve) => window.setTimeout(resolve, 700));
      }
      if (!response) throw new Error("The execution runtime did not respond.");
      const body = await response.json() as ExecutionResult & { detail?: string };
      if (!response.ok) throw new Error(body.detail ?? `Execution API returned ${response.status}`);
      setResult(body);
    } catch (reason) {
      setResult({ success: false, stdout: "", stderr: reason instanceof Error ? reason.message : "Execution failed.", result: null, table_preview: null, plots: [], duration_ms: 0, replayed_cells: 0, dataset: dataset as DatasetInfo });
    } finally { setRunning(false); }
  };

  return (
    <div className="code-learning-unit">
      {showInstruction && <p className="section-body code-purpose">{instruction}</p>}
      <div className="executable-cell">
      <div className="code-heading">
        <div className="code-heading-left">
          <span className="code-language-label">Python</span>
          {dataset && (
            <span className="code-file-label">{dataset.runtime_filename}</span>
          )}
        </div>
        <div className="code-heading-actions">
          <button type="button" className="code-action-btn" onClick={copyCode}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button type="button" className="code-action-btn" onClick={resetCode} disabled={running}>
            Reset
          </button>
        </div>
      </div>

      <textarea
        ref={editorRef}
        aria-label="Executable Python code"
        disabled={running}
        spellCheck={false}
        value={code}
        onChange={(event) => { setCode(event.target.value); setResult(null); setEditStatus(""); }}
      />

      <div className="cell-toolbar">
        {editStatus && <p className="cell-edit-status" role="status">{editStatus}</p>}
        <button
          type="button"
          className="run-code-button"
          disabled={running || !code.trim()}
          onClick={run}
        >
          {running ? "Running…" : "Run code"}
        </button>
      </div>

        {result && (
        <div className={result.success ? "cell-output success" : "cell-output error"}>
          <div className="output-status-bar">
            <strong>{result.success ? "EXECUTION SUCCESS" : "EXECUTION ERROR"}</strong>
            <span>{result.duration_ms} ms · {result.replayed_cells} prior cells replayed</span>
          </div>
          {result.stdout && <pre className="output-stdout">{result.stdout}</pre>}
          {result.stderr && <pre className="output-stderr">{result.stderr}</pre>}
          {result.table_preview ? (
            <DataTable columns={result.table_preview.columns} rows={result.table_preview.rows} />
          ) : result.result !== null && (
            <pre className="output-raw">{typeof result.result === "string" ? result.result : JSON.stringify(result.result, null, 2)}</pre>
          )}
          {result.plots?.length > 0 && (
            <div className="cell-plots">
              {result.plots.map((plot, index) => (
                <img src={plot} alt={`Generated plot ${index + 1}`} key={index} />
              ))}
            </div>
          )}
        </div>
        )}
      </div>

      {(codeExplanation.length > 0 || tryThis.length > 0) && <div className="code-guidance-grid">
        {codeExplanation.length > 0 && <section className="code-explanation" aria-labelledby={`code-explanation-${stage}`}>
          <div className="code-guidance-heading">
            <svg className="lesson-highlight-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-13-2 16" /></svg>
            <h5 id={`code-explanation-${stage}`}>How the code works</h5>
          </div>
          <ol className="code-explanation-list">{codeExplanation.map((explanation, index) => {
            const separator = /\s+[—–-]\s+/.exec(explanation);
            const element = separator ? explanation.slice(0, separator.index).trim().replace(/^`+|`+$/g, "") : null;
            const description = separator ? explanation.slice(separator.index + separator[0].length).trim() : explanation;
            return <li key={`${index}.${explanation}`}>
              <span className="code-explanation-number" aria-hidden="true">{index + 1}</span>
              <div className="code-explanation-copy">
                {element && <code>{element}</code>}
                <p>{description}</p>
              </div>
            </li>;
          })}</ol>
        </section>}
        {tryThis.length > 0 && <section className="try-this">
          <h5>Try this · explore the code</h5>
          {experiments.length > 0 ? <>
            <p>Apply an edit below to the cell above, then select Run code. Use Reset before trying another edit.</p>
            <ol className="code-experiments">{experiments.map((experiment, index) => {
              const original = section.code ?? "";
              const originalStart = original.indexOf(experiment.find);
              const start = code.indexOf(experiment.find);
              const matches = Boolean(experiment.find) && originalStart >= 0 && originalStart === original.lastIndexOf(experiment.find) && start >= 0 && start === code.lastIndexOf(experiment.find);
              const line = original.slice(0, originalStart).split("\n").length;
              const applied = appliedExperiment === index;
              return <li key={`${index}.${experiment.title}`}>
                <h6>{experiment.title}</h6>
                <span className="experiment-label">Find in the original cell{originalStart >= 0 ? ` · line ${line}` : ""}</span>
                <pre><code>{experiment.find}</code></pre>
                <span className="experiment-label">Replace with</span>
                <pre className="experiment-replacement"><code>{experiment.replace}</code></pre>
                <p><strong>What to look for:</strong> {experiment.expected_change}</p>
                <button type="button" className="experiment-apply" disabled={running || !matches || appliedExperiment !== null} onClick={() => applyExperiment(experiment, index)}>{applied ? "Applied to editor" : "Apply to editor"}</button>
                {(appliedExperiment !== null || !matches) && <p className="experiment-note">{applied ? "Run code above to see the change. Reset restores the original." : "Reset the cell to its original code before applying this edit."}</p>}
              </li>;
            })}</ol>
          </> : <p>Exact code edits aren’t available for this saved lesson.</p>}
        </section>}
      </div>}
    </div>
  );
}

function DataTable({ columns, rows }: { columns: string[]; rows: Record<string, unknown>[] }) {
  return (
    <div className="cell-table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => <th key={column}>{column}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => <td key={column}>{String(row[column] ?? "")}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function sectionLabel(type: LessonSection["type"]): string {
  return {
    meaning: "Main idea",
    concept: "Another way to understand it",
    analogy: "An analogy",
    example: "A small example",
    code: "Try the code",
    result: "Expected result",
    why_it_matters: "Why this matters",
    concept_bridge: "Concept connection",
    real_life_analogy: "Analogy",
    data_preview: "Dataset preview",
    pipeline: "Pipeline",
    transformation: "Data transformation",
    warning: "Watch out",
    metric: "Evaluation"
  }[type];
}
