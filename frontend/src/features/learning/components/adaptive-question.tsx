"use client";

import { useEffect, useRef, useState } from "react";
import type { QuestionItem } from "@/features/learning/lib/question-bank";
import { API_URL } from "@/lib/auth";

export default function AdaptiveQuestion({ items, required = true, onAttempt, onPresented }: { items: QuestionItem[]; required?: boolean; onAttempt: (item: QuestionItem, answer: string, correct: boolean, attempt: number, responseTimeMs: number, presentationId: string) => void; onPresented: (item: QuestionItem, presentationId: string) => void }) {
  const [itemIndex, setItemIndex] = useState(0);
  const [answer, setAnswer] = useState<string>(items[0]?.starterCode ?? "");
  const [checked, setChecked] = useState(false);
  const [mastered, setMastered] = useState(false);
  const [attempt, setAttempt] = useState(1);
  const [evaluating, setEvaluating] = useState(false);
  const [result, setResult] = useState<{ correct: boolean; feedback: string } | null>(null);
  const [presentationId, setPresentationId] = useState(() => crypto.randomUUID());
  const shownAt = useRef<number | null>(null);
  const onPresentedRef = useRef(onPresented);
  const item = items[itemIndex];
  const correct = result?.correct ?? answer === item.correctAnswer;

  useEffect(() => {
    onPresentedRef.current = onPresented;
  }, [onPresented]);

  useEffect(() => {
    shownAt.current = Date.now();
    onPresentedRef.current(items[itemIndex], presentationId);
  }, [itemIndex, items, presentationId]);

  const check = async () => {
    if (!answer.trim()) return;
    let evaluation = { correct: answer === item.correctAnswer, feedback: item.explanation };
    if (item.answerType === "code" && item.evaluatorId) {
      setEvaluating(true);
      try {
        const response = await fetch(`${API_URL}/api/code/evaluate`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ evaluator_id: item.evaluatorId, code: answer }) });
        if (!response.ok) throw new Error("evaluation failed");
        evaluation = await response.json() as { correct: boolean; feedback: string };
      } catch {
        setResult({ correct: false, feedback: "The code evaluator is unavailable. Please try again." });
        setEvaluating(false);
        return;
      }
      setEvaluating(false);
    }
    setResult(evaluation);
    setChecked(true);
    if (evaluation.correct) setMastered(true);
    onAttempt(item, answer, evaluation.correct, attempt, Date.now() - (shownAt.current ?? Date.now()), presentationId);
  };

  const tryAnother = () => {
    setItemIndex((itemIndex + 1) % items.length);
    const next = items[(itemIndex + 1) % items.length];
    setAnswer(next.starterCode ?? "");
    setPresentationId(crypto.randomUUID());
    setChecked(false);
    setResult(null);
    setAttempt(attempt + 1);
    shownAt.current = Date.now();
  };

  return <section className={`question-block ${required ? "required-action" : "evidence-action"}`}>
    <div className="action-heading"><p className="question-label">{required ? "Mastery action" : "Learner action"} · {item.typeLabel}</p><span>Type {itemIndex + 1} of {items.length}</span></div>
    {attempt > 1 && <p className="selection-reason"><strong>Same step, new approach.</strong> LEAP selected a different predefined question type after the previous response.</p>}
    <h4>{item.prompt}</h4>
    {item.answerType === "code" ? <textarea className="code-answer" aria-label="Python code answer" spellCheck={false} disabled={mastered || checked || evaluating} value={answer} onChange={(event) => setAnswer(event.target.value)} /> : <div className="answers">{item.options.map((option) => <button disabled={mastered || checked} className={answer === option ? "answer selected" : "answer"} onClick={() => setAnswer(option)} key={option}>{option}</button>)}</div>}
    <button className="check-button" disabled={!answer.trim() || mastered || checked || evaluating} onClick={check}>{evaluating ? "Running safely…" : mastered ? "Mastered" : checked ? "Answer recorded" : item.answerType === "code" ? "Run & check code" : "Check answer"}</button>
    {checked && <p className={correct ? "feedback correct" : "feedback incorrect"}>{correct ? `Correct. ${item.explanation}` : `Not yet. ${result?.feedback ?? item.explanation}`}</p>}
    {checked && !correct && <div className="same-step-plan"><strong>Re-plan this same step</strong><p>LEAP identified <code>{item.misconception}</code>. Stay here and approach the concept through another question format.</p><button className="alternate-button" onClick={tryAnother}>Try a different question type →</button></div>}
  </section>;
}
