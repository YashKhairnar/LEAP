"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import RichText from "@/features/workshop/components/rich-text";
import { saveWorkshopAnswer, type WorkshopQuestion } from "@/features/workshop/lib/workshop-api";

export type QuestionsHandle = { saveAll: () => Promise<void> };
type Status = "idle" | "saving" | "saved" | "error";

type Props = {
  stepLabel: string;
  questions: WorkshopQuestion[];
  saved: Record<string, { answer: string; saved_at: string }>;
  onSaved: (questionId: string, answer: string, savedAt: string) => void;
};

/** "Check your understanding" prompts and the "Your answers" boxes, saved as the learner types. */
const WorkshopQuestions = forwardRef<QuestionsHandle, Props>(function WorkshopQuestions({ stepLabel, questions, saved, onSaved }, ref) {
  const [answers, setAnswers] = useState<Record<string, string>>(() => Object.fromEntries(questions.map((question) => [question.question_id, saved[question.question_id]?.answer ?? ""])));
  const [status, setStatus] = useState<Record<string, Status>>({});
  const lastSaved = useRef<Record<string, string>>(Object.fromEntries(questions.map((question) => [question.question_id, saved[question.question_id]?.answer ?? ""])));
  const timers = useRef<Record<string, number>>({});

  const save = async (questionId: string, value: string) => {
    window.clearTimeout(timers.current[questionId]);
    if (lastSaved.current[questionId] === value) return;
    setStatus((current) => ({ ...current, [questionId]: "saving" }));
    try {
      const result = await saveWorkshopAnswer(questionId, value);
      lastSaved.current[questionId] = value;
      onSaved(questionId, value, result.saved_at);
      setStatus((current) => ({ ...current, [questionId]: "saved" }));
    } catch {
      setStatus((current) => ({ ...current, [questionId]: "error" }));
    }
  };

  useImperativeHandle(ref, () => ({ saveAll: async () => { await Promise.all(questions.map((question) => save(question.question_id, answers[question.question_id] ?? ""))); } }));
  useEffect(() => { const pending = timers.current; return () => Object.values(pending).forEach((timer) => window.clearTimeout(timer)); }, []);

  const change = (questionId: string, value: string) => {
    setAnswers((current) => ({ ...current, [questionId]: value }));
    setStatus((current) => ({ ...current, [questionId]: "idle" }));
    window.clearTimeout(timers.current[questionId]);
    timers.current[questionId] = window.setTimeout(() => void save(questionId, value), 1200);
  };

  return <>
    <section className="ws-box ws-box-check" aria-labelledby={`check-${stepLabel}`}>
      <h4 id={`check-${stepLabel}`}>Check your understanding</h4>
      {questions.map((question) => <p key={question.question_id}><strong>{question.question_id}:</strong> <RichText text={question.prompt} /></p>)}
      <p><em>Type your answers in the boxes below, in your own words.</em></p>
    </section>
    <section className="ws-answers" aria-label={`Your answers – ${stepLabel}`}>
      <h3>Your answers – {stepLabel}</h3>
      {questions.map((question) => {
        const state = status[question.question_id] ?? "idle";
        return <div className="ws-answer" key={question.question_id}>
          <label htmlFor={`answer-${question.question_id}`}>{question.question_id}</label>
          <textarea
            id={`answer-${question.question_id}`}
            rows={3}
            maxLength={5000}
            placeholder="Insert text here"
            value={answers[question.question_id] ?? ""}
            onChange={(event) => change(question.question_id, event.target.value)}
            onBlur={(event) => void save(question.question_id, event.target.value)}
          />
          <span className={`ws-save-status is-${state}`} role="status">
            {state === "saving" ? "Saving…" : state === "saved" ? "Saved" : state === "error" ? "Not saved. Check your connection; we’ll try again when you leave this box." : ""}
          </span>
        </div>;
      })}
    </section>
  </>;
});

export default WorkshopQuestions;
