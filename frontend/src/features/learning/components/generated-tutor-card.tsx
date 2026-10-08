"use client";
/* eslint-disable @next/next/no-img-element -- Codapi returns dynamic data-URL plots. */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { API_URL, getAuth } from "@/lib/auth";
import { INSTRUCTIONAL_ACTIONS, type InstructionalActionType, type InstructionalStep } from "@/features/learning/lib/instructional-actions";
import { collectionPlannerDecision, withCollectionContent, type CollectionContent, type QuestionItem } from "@/features/learning/lib/question-bank";
import { enqueueCollection, learningSessionId } from "@/features/collection/lib/collection";
import { questionContentId } from "@/features/collection/lib/content-id";
import { QuestionExposureClock, evidenceKind, type AttemptEvidence } from "@/features/collection/lib/question-exposure";

type TutorContent = { question: string; options: string[]; expected_answer: string; hint: string; explanation: string; concepts_tested: string[] };
type LessonSectionType = "meaning" | "concept" | "analogy" | "example" | "code" | "result" | "why_it_matters" | "concept_bridge" | "real_life_analogy" | "data_preview" | "pipeline" | "transformation" | "warning" | "metric";
type LessonSection = { type: LessonSectionType; title: string; body: string; items: string[]; code: string | null; language: string | null };
type CodeExperiment = { title: string; find: string; replace: string; expected_change: string };
type LessonContent = { title: string; introduction: string; sections: LessonSection[]; code_explanation?: string[]; try_this?: (CodeExperiment | string)[]; key_takeaway?: string };

export default function GeneratedTutorCard({ task, stage, step, actionType, lessonContext, learningObjectives, onAttempt, onPresented, onRestoredCorrect, reviewOnly = false }: {
  task: string; stage: string; step: InstructionalStep; actionType: InstructionalActionType; lessonContext: string; learningObjectives: string[];
  onAttempt: (item: QuestionItem, answer: string, correct: boolean, attempt: number, responseTimeMs: number, presentationId: string, evidence: AttemptEvidence) => Promise<void>;
  onPresented: (item: QuestionItem, presentationId: string) => void;
  onRestoredCorrect?: (step: InstructionalStep) => void;
  reviewOnly?: boolean;
}) {
  const learner = getAuth()?.user;
  const lessonKey = `leap.generated.lesson.v18.${learner?.user_id ?? "anonymous"}.${learner?.analogy_preference ?? "java"}.${task}.${stage}`;
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
  const [viewMode, setViewMode] = useState<"split" | "learn" | "practice">("learn");
  const practiceNoticeKey = `leap.practice.personalization-notice.v1.${learner?.user_id ?? "anonymous"}.${task}`;
  const [personalizationNoticeAcknowledged, setPersonalizationNoticeAcknowledged] = useState(() => {
    if (typeof window === "undefined" || reviewOnly || step !== "practice") return true;
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
            options: saved.content.options, correctAnswer: saved.content.expected_answer,
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
      const nextItem: QuestionItem = { id: `generated.${body.content_instance_id}`, step, actionType: effectiveAction, typeLabel: "LLM-generated question", prompt: content.question, options: content.options, correctAnswer: content.expected_answer, explanation: content.explanation, misconception: "generated_question_incorrect", learningObjectives: content.concepts_tested.length ? content.concepts_tested : learningObjectives, lessonContent: body.lesson, plannerDecision: effectiveDecision, selectionPolicy: assignmentPolicy, generationMetadata: { schema_version: "stage_sections_question_v3", prompt_version: body.prompt_version, code_version: body.code_version, curriculum_layout: "stage_sections_question_v3", model: body.model, dataset: body.dataset, task, stage, step, selected_action_type: effectiveAction, assignment_policy: assignmentPolicy, selection_probability: effectiveDecision?.selection_probability, content_instance_id: body.content_instance_id, curriculum_context: lessonContext, requested_learning_objectives: learningObjectives, lesson_reused: cachedLesson !== null, generated_at: new Date().toISOString() } };
      const nextPresentationId = crypto.randomUUID();
      setGenerated({ model: body.model, lesson: body.lesson, content }); setItem(withCollectionContent(nextItem, body.collection_content)); setPresentationId(nextPresentationId);
      setAttempt(1); hintUsed.current = false; answerRevealed.current = false; historyKnown.current = true;
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
    answerRevealed.current = true;
    const saving = onAttemptRef.current(item, answer, correct, attempt, duration, presentationId, evidence);
    recordExposure("answer_revealed");
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
  const showPersonalizationNotice = Boolean(generated && item && !reviewOnly && step === "practice" && !checked && !personalizationNoticeAcknowledged);

  const acknowledgePersonalizationNotice = () => {
    window.localStorage.setItem(practiceNoticeKey, "acknowledged");
    setPersonalizationNoticeAcknowledged(true);
  };

  return <section className="generated-tutor-card" aria-live="polite">
    <header className="card-top-toolbar">
      <div className="card-meta-tags">
        <span className="lesson-location">{stage.replace(/_/g, " ")}</span>
        <span aria-hidden="true">/</span>
        <strong>{step}</strong>
      </div>
      <div className="view-mode-selector" role="tablist" aria-label="Layout mode">
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === "split"}
          className={`view-mode-btn ${viewMode === "split" ? "active" : ""}`}
          onClick={() => setViewMode("split")}
        >
          Split view
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === "learn"}
          className={`view-mode-btn ${viewMode === "learn" ? "active" : ""}`}
          onClick={() => setViewMode("learn")}
        >
          Lesson
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === "practice"}
          className={`view-mode-btn ${viewMode === "practice" ? "active" : ""}`}
          onClick={() => setViewMode("practice")}
        >
          Practice
        </button>
      </div>
    </header>

    {!stageLesson && loading && (
      <div className="card-loading-state">
        <div className="loading-pulse-line" />
        <p>{reviewOnly ? "Loading your saved lesson…" : "Preparing lesson and personalized instructional guidance..."}</p>
      </div>
    )}

    {!stageLesson && error && (
      <div className="card-error-state">
        <span className="error-pill">{reviewOnly ? "SAVED LESSON UNAVAILABLE" : "GENERATION ERROR"}</span>
        <p className="generated-tutor-error">{error}</p>
        <button className="alternate-button" onClick={regenerate}>Try again</button>
      </div>
    )}

    {reviewOnly && !stageLesson && !loading && !error && <p className="question-loading">No saved lesson is available for this stage yet.</p>}

    {stageLesson && (
      <div className={`generated-learning-workspace mode-${viewMode}`}>
        {(viewMode === "split" || viewMode === "learn") && (
          <article className="generated-lesson-pane">
            <h3 className="lesson-heading">{stageLesson.title}</h3>
            <p className="lead">{stageLesson.introduction}</p>

            <div className="dynamic-lesson-sections">
              {stageLesson.sections.map((section, index) => {
                const nextSection = stageLesson.sections[index + 1];
                const previousSection = stageLesson.sections[index - 1];
                if (section.type === "code" && previousSection?.type === "example") return null;
                if (section.type === "example" && nextSection?.type === "code") return <div className="example-code-pair" key="example-code-pair">
                  <LessonSectionView section={section} task={task} stage={stage} step={step} />
                  <LessonSectionView section={nextSection} task={task} stage={stage} step={step} codeExplanation={stageLesson.code_explanation} tryThis={stageLesson.try_this} />
                </div>;
                return <LessonSectionView section={section} task={task} stage={stage} step={step} codeExplanation={stageLesson.code_explanation} tryThis={stageLesson.try_this} key={`${section.type}.${index}`} />;
              })}
            </div>

            {stageLesson.key_takeaway && <aside className="key-takeaway" aria-label="Key takeaway">
              <span><svg className="lesson-highlight-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6" /></svg>Key takeaway</span>
              <p>{stageLesson.key_takeaway}</p>
            </aside>}

            {viewMode === "learn" && (
              <div className="pane-jump-footer">
                <button type="button" className="primary-button" onClick={() => setViewMode("practice")}>
                  {reviewOnly ? "View saved question →" : "Try the practice question →"}
                </button>
              </div>
            )}
          </article>
        )}

        {(viewMode === "split" || viewMode === "practice") && (
          <aside className="generated-question-pane">
            <div className="question-pane-heading">
              <div>
                <span className="pane-label">PRACTICE</span>
                <span className="attempt-counter">ATTEMPT {attempt}</span>
              </div>
              {!reviewOnly && <button className="text-button" onClick={regenerate}>New question</button>}
            </div>

            {loading && <p className="question-loading">{reviewOnly ? "Loading your saved question…" : "Preparing your next practice question…"}</p>}
            
            {error && (
              <div className="card-error-state">
                <span className="error-pill">ERROR</span>
                <p className="generated-tutor-error">{error}</p>
                <button className="alternate-button" onClick={regenerate}>Try again</button>
              </div>
            )}

            {reviewOnly && !loading && !error && !item && <p className="question-loading">No saved question is available for this step.</p>}

            {showPersonalizationNotice && (
              <section className="practice-personalization-notice" aria-labelledby="practice-personalization-title">
                <span className="practice-notice-label">Before your first practice question</span>
                <h3 id="practice-personalization-title">How LEAP personalizes your practice</h3>
                <p>Your response helps LEAP estimate what is clear and where another approach may help. For each practice question, LEAP records:</p>
                <ul>
                  <li>Your answer and whether it was correct</li>
                  <li>Your attempt count and whether you opened a hint</li>
                  <li>Your active response time while the question is visible</li>
                </ul>
                <p>LEAP uses this learning history to choose how later questions approach the concept. This practice supports your learning; it is separate from the final assessment score.</p>
                <div className="practice-notice-actions">
                  <button className="primary-button" type="button" onClick={acknowledgePersonalizationNotice}>I understand — start practice</button>
                  <Link href="/privacy" target="_blank">Read the data notice</Link>
                </div>
              </section>
            )}

            {generated && item && !showPersonalizationNotice && (
              <div ref={questionElement}>
                <div className="generated-question-section">
                  <span className="question-kicker">CHECK YOUR UNDERSTANDING</span>
                  <p className="generated-question">{item.prompt}</p>
                </div>

                <div className="answers-grid">
                  {item.options.map((option, index) => {
                    const letter = ["A", "B", "C", "D"][index] ?? String.fromCharCode(65 + index);
                    const isSelected = answer === option;
                    let optionStatusClass = "";

                    if (checked) {
                      if (isSelected && correct) {
                        optionStatusClass = "answer-correct-chosen";
                      } else if (isSelected && !correct) {
                        optionStatusClass = "answer-incorrect-chosen";
                      } else if (!isSelected && option === item.correctAnswer) {
                        optionStatusClass = "answer-revealed-correct";
                      } else {
                        optionStatusClass = "answer-dimmed";
                      }
                    } else if (isSelected) {
                      optionStatusClass = "selected";
                    }

                    return (
                      <button
                        type="button"
                        disabled={checked || reviewOnly}
                        className={`answer-card ${optionStatusClass}`}
                        onClick={() => setAnswer(option)}
                        key={option}
                      >
                        <span className="answer-letter">{letter}</span>
                        <span className="answer-text">{option}</span>
                        {checked && option === item.correctAnswer && (
                          <span className="status-badge correct-badge">CORRECT</span>
                        )}
                        {checked && isSelected && !correct && (
                          <span className="status-badge incorrect-badge">SELECTED</span>
                        )}
                      </button>
                    );
                  })}
                </div>

                <div className="generated-tutor-actions">
                  <button
                    className="check-button"
                    disabled={reviewOnly || !answer.trim() || checked}
                    onClick={() => void check(performance.now())}
                  >
                    {reviewOnly ? "SAVED ANSWER" : checked ? "ANSWER RECORDED" : "CHECK ANSWER"}
                  </button>
                  <button
                    type="button"
                    className="hint-toggle-button"
                    onClick={() => { if (!showHint) { hintUsed.current = true; recordExposure("hint_opened"); } setShowHint((value) => !value); }}
                  >
                    {showHint ? "HIDE HINT" : "NEED A HINT?"}
                  </button>
                </div>

                {showHint && (
                  <div className="hint-card">
                    <div className="hint-header">
                      <span className="hint-kicker">HINT GUIDANCE</span>
                    </div>
                    <p className="hint-body">{generated.content.hint}</p>
                  </div>
                )}

                {checked && (
                  <div className={`feedback-card ${correct ? "feedback-correct" : "feedback-incorrect"}`}>
                    <div className="feedback-header">
                      <span className={`feedback-tag ${correct ? "tag-success" : "tag-error"}`}>
                        {correct ? "CORRECT" : "NOT QUITE"}
                      </span>
                      {!correct && (
                        <span className="expected-answer-label">
                          Expected Answer: <strong>{item.correctAnswer}</strong>
                        </span>
                      )}
                    </div>
                    <p className="feedback-explanation">{item.explanation}</p>
                    {!correct && !reviewOnly && (
                      <div className="feedback-actions">
                        <button className="alternate-button" type="button" onClick={retryCurrentQuestion}>Try again</button>
                        <button className="alternate-button" type="button" disabled={loading} onClick={() => void tryAnotherAfterIncorrect()}>{loading ? "Preparing…" : "Try a similar question"}</button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {viewMode === "practice" && (
              <div className="pane-jump-footer">
                <button type="button" className="text-button" onClick={() => setViewMode("learn")}>
                  ← Back to Full Lesson Guide
                </button>
              </div>
            )}
          </aside>
        )}
      </div>
    )}
  </section>;
}

function normalize(value: string): string { return value.trim().toLocaleLowerCase(); }

function repeatsCode(body: string, code: string | null): boolean {
  if (!code) return false;
  const compact = (value: string) => value.toLocaleLowerCase().replace(/[\s`]+/g, "").replace(/;+/g, "");
  const compactBody = compact(body);
  const compactCode = compact(code);
  return compactBody === compactCode || compactBody.includes(compactCode);
}

function LessonSectionView({ section, task, stage, step, codeExplanation = [], tryThis = [] }: { section: LessonSection; task: string; stage: string; step: InstructionalStep; codeExplanation?: string[]; tryThis?: (CodeExperiment | string)[] }) {
  const isOrderedList = section.type === "pipeline" || section.type === "transformation";

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
      
      {section.type !== "code" && section.items.length > 0 && (
        isOrderedList ? (
          <ol className="section-bullet-list">
            {section.items.map((item) => <li key={item}>{item}</li>)}
          </ol>
        ) : (
          <ul className="section-bullet-list">
            {section.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )
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

function ExecutableLessonCell({ section, task, stage, step, codeExplanation, tryThis }: { section: LessonSection; task: string; stage: string; step: InstructionalStep; codeExplanation: string[]; tryThis: (CodeExperiment | string)[] }) {
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
    ? "Run this focused stage code, then compare its output or new state with the Result section below."
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
      const response = await fetch(`${API_URL}/api/code/run`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ execution_id: crypto.randomUUID(), session_id: window.sessionStorage.getItem("leap.learning.session.v1"), task, stage, step, code }),
      });
      const body = await response.json() as ExecutionResult & { detail?: string };
      if (!response.ok) throw new Error(body.detail ?? `Execution API returned ${response.status}`);
      setResult(body);
    } catch (reason) {
      setResult({ success: false, stdout: "", stderr: reason instanceof Error ? reason.message : "Execution failed.", result: null, table_preview: null, plots: [], duration_ms: 0, replayed_cells: 0, dataset: dataset as DatasetInfo });
    } finally { setRunning(false); }
  };

  return (
    <div className="code-learning-unit">
      <p className="section-body code-purpose">{instruction}</p>
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
        {tryThis.length > 0 && <details className="try-this" open>
          <summary>Try this · explore the code</summary>
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
        </details>}
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
    meaning: "1. Meaning",
    concept: "2. Core ML concept",
    analogy: "2. Analogy",
    example: "3. Example",
    code: "4. Code",
    result: "5. Result",
    why_it_matters: "6. Why it matters",
    concept_bridge: "Concept connection",
    real_life_analogy: "Analogy",
    data_preview: "Dataset preview",
    pipeline: "Pipeline",
    transformation: "Data transformation",
    warning: "Watch out",
    metric: "Evaluation"
  }[type];
}
