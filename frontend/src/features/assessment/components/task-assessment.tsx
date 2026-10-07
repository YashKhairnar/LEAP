"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { API_URL, getAuth } from "@/lib/auth";
import { flushCollectionQueue } from "@/features/collection/lib/collection";

type AssessmentQuestion = { id: string; stage: string; concept: string; prompt: string; options: string[]; code: string | null };
type QuestionReview = AssessmentQuestion & { answer: number; selected: number; correct: boolean; explanation: string };
type AssessmentResult = { score: number; total: number; submitted_at: string; questions: QuestionReview[] };
type AssessmentPhase = "pre" | "post";
type Assessment = { phase: AssessmentPhase; version: string; unlocked: boolean; preview_allowed?: boolean; baseline_score?: number | null; questions: AssessmentQuestion[]; result: AssessmentResult | null };

export default function TaskAssessment({ task, phase = "post", onReview }: { task: string; phase?: AssessmentPhase; onReview?: (stage: string) => void }) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const submissionInFlight = useRef(false);
  const draftKey = useRef<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true); setError("");
    try {
      // Stage-completion events may still be queued when this view first opens.
      await flushCollectionQueue().catch(() => undefined);
      const response = await fetch(`${API_URL}/api/assessments/${encodeURIComponent(task)}?phase=${phase}`, { credentials: "include", cache: "no-store", signal });
      if (!response.ok) throw new Error("Could not load your assessment. Check your connection and try again.");
      const body = await response.json() as Assessment;
      if (signal?.aborted) return;
      const userId = getAuth()?.user.user_id;
      draftKey.current = userId && body.unlocked ? `leap.assessment.draft.${phase}.${body.version}.${userId}.${task}` : null;
      const restored: Record<string, number> = {};
      try {
        const saved = draftKey.current && window.sessionStorage.getItem(draftKey.current);
        const draft = saved ? JSON.parse(saved) as Record<string, number> : {};
        if (!body.result) for (const question of body.questions) {
          const value = draft[question.id];
          if (Number.isInteger(value) && value >= 0 && value < question.options.length) restored[question.id] = value;
        }
      } catch { /* Browser storage is optional; the submitted result lives on the server. */ }
      setAnswers(restored);
      setAssessment(body);
    } catch (reason) {
      if (!signal?.aborted) setError(reason instanceof Error ? reason.message : "Unable to load the assessment.");
    } finally { if (!signal?.aborted) setLoading(false); }
  }, [phase, task]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [load]);

  const choose = (id: string, value: number) => {
    const next = { ...answers, [id]: value };
    setAnswers(next);
    try { if (draftKey.current) window.sessionStorage.setItem(draftKey.current, JSON.stringify(next)); } catch { /* Optional draft storage. */ }
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!assessment || !assessment.unlocked || assessment.result || submissionInFlight.current || assessment.questions.some((question) => answers[question.id] === undefined)) return;
    submissionInFlight.current = true;
    setSubmitting(true); setError("");
    try {
      const response = await fetch(`${API_URL}/api/assessments/${encodeURIComponent(task)}?phase=${phase}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: assessment.version, answers }),
      });
      const body = await response.json() as AssessmentResult & { detail?: unknown };
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Your result could not be saved. Your answers are still here; please try again.");
      setAssessment({ ...assessment, result: body });
      try { if (draftKey.current) window.sessionStorage.removeItem(draftKey.current); } catch { /* Optional draft storage. */ }
      requestAnimationFrame(() => {
        resultHeading.current?.focus({ preventScroll: true });
        resultHeading.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Your result could not be saved. Please try again.");
    } finally { submissionInFlight.current = false; setSubmitting(false); }
  };

  const isPre = phase === "pre";
  const title = isPre ? "Before-learning assessment" : "Final task assessment";
  if (loading) return <p className="question-loading" role="status">Preparing your {isPre ? "starting" : "final"} assessment…</p>;
  if (!assessment) return <section className="task-assessment"><p role="alert">{error}</p><button className="primary-button" type="button" onClick={() => void load()}>Try again</button></section>;
  if (!assessment.unlocked && !assessment.preview_allowed) return <section className="task-assessment"><h2>{title}</h2><p>Complete all six stages to open these questions. Previewing is disabled during data collection.</p><button className="primary-button" type="button" onClick={() => void load()}>Check progress</button></section>;

  const result = assessment.result;
  const answered = assessment.questions.filter((question) => answers[question.id] !== undefined).length;
  const revisit = result ? [...new Map(result.questions.filter((question) => !question.correct).map((question) => [question.stage, question])).values()] : [];

  return <section className="task-assessment" aria-labelledby="assessment-title">
    <header className="assessment-header">
      <p className="eyebrow blue">{isPre ? "Before you begin" : assessment.unlocked ? "All six lesson stages completed" : "Assessment preview"}</p>
      <h2 id="assessment-title">{title}</h2>
      <p>{isPre ? "Answer these same questions again after learning so we can compare your performance before and after the task." : "Put the whole pipeline together: data, preparation, training, prediction, and evaluation."}</p>
    </header>
    {result ? <>
      <section className="assessment-score" aria-labelledby="assessment-result-title">
        <div><h3 id="assessment-result-title" ref={resultHeading} tabIndex={-1}>{isPre ? "Starting assessment submitted" : "Assessment submitted"}</h3><p>Your first submission is saved to your account. Review the reasoning below.</p></div>
        <strong aria-label={`${result.score} out of ${result.total} correct`}>{result.score}<span> / {result.total}</span><small>{Math.round(result.score / result.total * 100)}% correct</small></strong>
      </section>
      {!isPre && assessment.baseline_score !== null && assessment.baseline_score !== undefined && <p className="assessment-comparison"><strong>Before learning:</strong> {assessment.baseline_score} / {result.total} · <strong>Change:</strong> {result.score - assessment.baseline_score >= 0 ? "+" : ""}{result.score - assessment.baseline_score} points</p>}
      {!isPre && revisit.length > 0 && <aside className="assessment-revisit"><h3>Stages to revisit</h3><div>{revisit.map((question) => <button className="text-button" type="button" key={question.stage} onClick={() => onReview?.(question.stage)}>{question.stage.replaceAll("_", " ")} →</button>)}</div></aside>}
      <div className="assessment-questions">{result.questions.map((question, index) => <section className="assessment-question assessment-reviewed" key={question.id}>
        <p className={`assessment-question-meta ${question.correct ? "is-correct" : "is-incorrect"}`}>Question {index + 1} · {question.correct ? "Correct" : "Incorrect"} · {question.concept}</p>
        <h3>{question.prompt}</h3>
        {question.code && <pre><code>{question.code}</code></pre>}
        <p><strong>Your answer:</strong> {question.options[question.selected]}</p>
        {!question.correct && <p><strong>Correct answer:</strong> {question.options[question.answer]}</p>}
        <p className="assessment-explanation"><strong>Why:</strong> {question.explanation}</p>
      </section>)}</div>
      <footer className="assessment-footer"><Link className="primary-button" href={isPre ? `/learn/${task}` : "/"}>{isPre ? "Begin learning" : "Return to dashboard"}</Link></footer>
    </> : <form onSubmit={submit}>
      <div className="assessment-instructions"><p><strong>10 questions · one correct answer each · 1 point per question.</strong></p><p>{isPre ? "Answer independently before starting the task. Your first submission is saved as your starting score." : assessment.unlocked ? "Answer independently, then submit all 10 to see your score and explanations. You can change answers before submitting. Your first submission is final; there is no pass/fail cutoff." : "You can preview all questions and select options now. Preview answers are not saved or scored. Complete the six lesson stages to submit your final assessment."}</p></div>
      <div className="assessment-progress"><label htmlFor="assessment-progress">{answered} of 10 answered</label><progress id="assessment-progress" max={10} value={answered} /></div>
      <div className="assessment-questions">{assessment.questions.map((question, index) => <fieldset className="assessment-question" disabled={submitting} key={question.id}>
        <legend><span className="assessment-question-meta">Question {index + 1} of 10</span><span>{question.prompt}</span></legend>
        {question.code && <pre><code>{question.code}</code></pre>}
        <div className="assessment-options">{question.options.map((option, optionIndex) => <label className={`assessment-option ${answers[question.id] === optionIndex ? "is-selected" : ""}`} key={optionIndex}>
          <input type="radio" name={question.id} value={optionIndex} checked={answers[question.id] === optionIndex} onChange={() => choose(question.id, optionIndex)} required />
          <span className="assessment-option-letter" aria-hidden="true">{String.fromCharCode(65 + optionIndex)}</span><span>{option}</span>
        </label>)}</div>
      </fieldset>)}</div>
      {error && <p className="assessment-error" role="alert">{error}</p>}
      <footer className="assessment-footer"><p role="status">{!assessment.unlocked ? "Preview only — your learning progress and assessment score are unchanged." : answered < 10 ? `${10 - answered} unanswered. Complete all questions to submit.` : "All questions answered. Ready to submit?"}</p><button className="primary-button" type="submit" disabled={!assessment.unlocked || submitting || answered !== 10}>{!assessment.unlocked ? "Complete stages to submit" : submitting ? "Saving your assessment…" : isPre ? "Save starting score" : "Submit assessment"}</button></footer>
    </form>}
  </section>;
}

export function AssessmentNavigation({ unlocked, selected = false, href, onClick }: { unlocked: boolean; selected?: boolean; href?: string; onClick?: () => void }) {
  const content = <><span className="stage-node" aria-hidden="true">Q</span><span className="stage-copy"><span>{unlocked ? "10 questions" : "After all six stages"}</span><strong>Final assessment</strong></span></>;
  return <li className={`stage assessment-stage ${selected ? "active selected-stage" : href || unlocked ? "next-stage" : "locked"}`}>
    {href ? <Link className="stage-navigation-button" data-stage-navigation aria-current={selected ? "step" : undefined} href={href}>{content}</Link> : <button className="stage-navigation-button" type="button" data-stage-navigation disabled={!unlocked} aria-current={selected ? "step" : undefined} onClick={onClick}>{content}</button>}
  </li>;
}
