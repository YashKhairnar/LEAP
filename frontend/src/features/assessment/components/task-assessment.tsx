"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { API_URL, getAuth } from "@/lib/auth";
import { flushCollectionQueue } from "@/features/collection/lib/collection";
import AssessmentReportView, { type AssessmentReport } from "@/features/assessment/components/assessment-report";

type AssessmentQuestion = { id: string; stage: string; concept: string; prompt: string; options: string[]; code: string | null };
type QuestionReview = AssessmentQuestion & { answer: number; selected: number; correct: boolean; explanation: string };
type AssessmentResult = { score: number; total: number; submitted_at: string; questions: QuestionReview[]; report?: AssessmentReport };
type AssessmentPhase = "pre" | "post";
// Same order as the learning paths on the home page; the last path leads back home.
const PATH_ORDER = [
  { slug: "sentiment", title: "Review sentiment" },
  { slug: "regression", title: "House prices" },
  { slug: "cnn", title: "Handwritten digits" },
];
type Assessment = { phase: AssessmentPhase; version: string; unlocked: boolean; preview_allowed?: boolean; baseline_score?: number | null; questions: AssessmentQuestion[]; result: AssessmentResult | null };

export default function TaskAssessment({ task, phase = "post", onReview }: { task: string; phase?: AssessmentPhase; onReview?: (stage: string) => void }) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [alreadySubmitted, setAlreadySubmitted] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [started, setStarted] = useState(phase === "pre");
  const [questionIndex, setQuestionIndex] = useState(0);
  const questionHeading = useRef<HTMLLegendElement>(null);
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
    if (!assessment || !assessment.unlocked || assessment.result || !confirming || submissionInFlight.current || assessment.questions.some((question) => answers[question.id] === undefined)) return;
    submissionInFlight.current = true;
    setSubmitting(true); setError("");
    try {
      const response = await fetch(`${API_URL}/api/assessments/${encodeURIComponent(task)}?phase=${phase}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: assessment.version, answers }),
      });
      const body = await response.json() as AssessmentResult & { detail?: unknown; already_submitted?: boolean };
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Your result could not be saved. Your answers are still here; please try again.");
      const { already_submitted: repeat, ...saved } = body;
      setAlreadySubmitted(Boolean(repeat));
      setAssessment({ ...assessment, result: saved });
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
  const taskSlug = task === "sentiment_classification" ? "sentiment" : task;
  const nextPath = PATH_ORDER[PATH_ORDER.findIndex((path) => path.slug === taskSlug) + 1];
  const title = isPre ? "Starting knowledge check" : "Final task assessment";
  if (loading) return <p className="question-loading" role="status">Preparing your {isPre ? "starting" : "final"} assessment…</p>;
  if (!assessment) return <section className="task-assessment"><p role="alert">{error}</p><button className="primary-button" type="button" onClick={() => void load()}>Try again</button></section>;
  if (!assessment.unlocked && !assessment.preview_allowed) return <section className="task-assessment"><h2>{title}</h2><p>Complete all six stages to open these questions. Previewing is disabled during data collection.</p><button className="primary-button" type="button" onClick={() => void load()}>Check progress</button></section>;

  const result = assessment.result;
  const answered = assessment.questions.filter((question) => answers[question.id] !== undefined).length;
  const currentQuestion = assessment.questions[questionIndex];
  const moveQuestion = (next: number) => {
    setConfirming(false);
    setQuestionIndex(next);
    requestAnimationFrame(() => {
      questionHeading.current?.focus({ preventScroll: true });
      questionHeading.current?.scrollIntoView({ block: "center", behavior: "smooth" });
    });
  };

  return <section className="task-assessment" aria-labelledby="assessment-title">
    <div className="assessment-mode-banner" role="status">
      <strong>{isPre ? "STARTING ASSESSMENT" : "FINAL ASSESSMENT"}</strong>
      <span>{isPre ? "This records what you know before any concepts are introduced." : assessment.unlocked ? "Check what you learned across all six stages." : "Complete all six stages before submitting."}</span>
    </div>
    <header className="assessment-header">
      <p className="eyebrow blue">{isPre ? "Before you begin" : assessment.unlocked ? "All six lesson stages completed" : "Assessment preview"}</p>
      <h2 id="assessment-title">{title}</h2>
      {!result && <p>{isPre ? "You are not expected to know these answers. Choose “I’m not sure yet” whenever you do not know—this is not a pass-or-fail test, and answers will not be shown before the lesson." : "Answer independently. You can go back and change your answers until you submit; after that they are final."}</p>}
    </header>
    {result ? <>
      <section className="assessment-score" aria-labelledby="assessment-result-title">
        <div><h3 id="assessment-result-title" ref={resultHeading} tabIndex={-1}>{isPre ? "Starting assessment saved" : "Assessment submitted"}</h3><p>{isPre ? "Your answers are saved without feedback and can’t be changed. After the lesson, the final assessment will show how your understanding changed." : "Your answers are final and can’t be changed. Your report and the answer review are below."}</p><p className="assessment-submitted-at">Submitted {new Date(result.submitted_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}</p></div>
        {!isPre && <strong aria-label={`${result.score} out of ${result.total} correct`}>{result.score}<span> / {result.total}</span><small>{Math.round(result.score / result.total * 100)}% correct</small></strong>}
      </section>
      {alreadySubmitted && <p className="assessment-already" role="status">You had already submitted this assessment, so your new answers were not saved. Your first submission is shown.</p>}
      {!isPre && result.report && <AssessmentReportView report={result.report} onReview={onReview} />}
      {!isPre && <section className="assessment-review-details"><h3>Review answers and explanations</h3>
      <div className="assessment-questions">{result.questions.map((question, index) => <section className="assessment-question assessment-reviewed" key={question.id}>
        <p className={`assessment-question-meta ${question.correct ? "is-correct" : "is-incorrect"}`}>Question {index + 1} · {question.correct ? "Correct" : "Incorrect"} · {question.concept}</p>
        <h3>{question.prompt}</h3>
        {question.code && <pre><code>{question.code}</code></pre>}
        <p><strong>Your answer:</strong> {question.options[question.selected]}</p>
        {!question.correct && <p><strong>Correct answer:</strong> {question.options[question.answer]}</p>}
        <p className="assessment-explanation"><strong>Why:</strong> {question.explanation}</p>
      </section>)}</div></section>}
      <footer className="assessment-footer">
        {isPre ? <Link className="primary-button" href={`/learn/${taskSlug}?view=dataset`}>Next: explore the dataset →</Link>
          : nextPath ? <><Link className="text-button" href="/">Back to learning paths</Link><Link className="primary-button" href={`/learn/${nextPath.slug}`}>Next: {nextPath.title} →</Link></>
          : <Link className="primary-button" href="/">Finish: back to learning paths →</Link>}
      </footer>
    </> : !started ? <div className="assessment-start">
      <p>10 questions · one answer each · no time limit</p>
      <p>{isPre ? "You can take it once. Your answers create a private starting point for comparison after learning." : "You can take it once: your first submission is final. Afterward you get a report on how your understanding changed, with explanations for every question."}</p>
      <button className="primary-button" type="button" onClick={() => setStarted(true)}>Begin {isPre ? "starting" : "final"} assessment →</button>
    </div> : <form onSubmit={submit}>
      <div className="assessment-progress"><label htmlFor="assessment-progress">{answered} of 10 answered</label><progress id="assessment-progress" max={10} value={answered} /></div>
      <div className="assessment-questions">{assessment.questions.slice(questionIndex, questionIndex + 1).map((question) => <fieldset className="assessment-question" disabled={submitting} key={question.id}>
        <legend ref={questionHeading} tabIndex={-1}><span className="assessment-question-meta">Question {questionIndex + 1} of 10</span><span>{question.prompt}</span></legend>
        {question.code && <pre><code>{question.code}</code></pre>}
        <div className="assessment-options">{question.options.map((option, optionIndex) => <label className={`assessment-option ${answers[question.id] === optionIndex ? "is-selected" : ""}`} key={optionIndex}>
          <input type="radio" name={question.id} value={optionIndex} checked={answers[question.id] === optionIndex} onChange={() => choose(question.id, optionIndex)} required />
          <span className="assessment-option-letter" aria-hidden="true">{String.fromCharCode(65 + optionIndex)}</span><span>{option}</span>
        </label>)}</div>
      </fieldset>)}</div>
      {confirming && <div className="assessment-confirm" role="alert">
        <strong>Submit all 10 answers?</strong>
        <span>You can only submit once. After this, your answers can’t be changed.</span>
      </div>}
      {error && <p className="assessment-error" role="alert">{error}</p>}
      <footer className="assessment-footer">
        <button className="text-button" type="button" disabled={questionIndex === 0 || submitting} onClick={() => moveQuestion(questionIndex - 1)}>← Previous</button>
        {questionIndex < assessment.questions.length - 1 ? <button className="primary-button" type="button" disabled={answers[currentQuestion.id] === undefined} onClick={() => moveQuestion(questionIndex + 1)}>Next question →</button> : !confirming || !assessment.unlocked
          ? <button key="review" className="primary-button" type="button" disabled={!assessment.unlocked || answered !== 10} onClick={() => setConfirming(true)}>{!assessment.unlocked ? "Complete stages to submit" : "Submit assessment"}</button>
          : <button key="confirm" className="primary-button" type="submit" disabled={submitting}>{submitting ? "Saving…" : "Yes, submit my answers"}</button>}
      </footer>
    </form>}
  </section>;
}

export function AssessmentNavigation({ unlocked, selected = false, href, onClick }: { unlocked: boolean; selected?: boolean; href?: string; onClick?: () => void }) {
  const content = <><span className="stage-node" aria-hidden="true">{unlocked ? "Q" : "🔒"}</span><span className="stage-copy"><span>{unlocked ? "10 questions" : "Locked · After all six stages"}</span><strong>Final assessment</strong></span></>;
  return <li className={`stage assessment-stage ${selected ? "active selected-stage" : unlocked ? "next-stage" : "locked"}`}>
    {unlocked && href ? <Link className="stage-navigation-button" data-stage-navigation aria-current={selected ? "step" : undefined} aria-label="Open final assessment" href={href}>{content}</Link> : <button className="stage-navigation-button" type="button" data-stage-navigation disabled={!unlocked} aria-current={selected ? "step" : undefined} aria-label={unlocked ? "Open final assessment" : "Final assessment locked until all six stages are complete"} onClick={onClick}>{content}</button>}
  </li>;
}

export function StartingAssessmentNavigation({ complete, href, selected = false }: { complete: boolean; href: string; selected?: boolean }) {
  return <li className={`stage starting-assessment-stage ${selected ? "active selected-stage" : complete ? "complete-stage" : "next-stage"}`}>
    <Link className="stage-navigation-button" data-stage-navigation aria-current={selected ? "step" : undefined} href={href}>
      <span className="stage-node" aria-hidden="true">{complete ? "✓" : "Q"}</span>
      <span className="stage-copy"><span>Before the lesson</span><strong>Starting assessment</strong></span>
    </Link>
  </li>;
}
