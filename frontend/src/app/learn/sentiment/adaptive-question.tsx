"use client";

import { useEffect, useRef, useState } from "react";
import type { QuestionItem } from "@/lib/question-bank";

export default function AdaptiveQuestion({ items, required = true, onAttempt }: { items: QuestionItem[]; required?: boolean; onAttempt: (item: QuestionItem, answer: string, correct: boolean, attempt: number, responseTimeMs: number) => void }) {
  const [itemIndex, setItemIndex] = useState(0);
  const [answer, setAnswer] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  const [mastered, setMastered] = useState(false);
  const [attempt, setAttempt] = useState(1);
  const shownAt = useRef<number | null>(null);
  const item = items[itemIndex];
  const correct = answer === item.correctAnswer;

  useEffect(() => {
    shownAt.current = Date.now();
  }, [itemIndex]);

  const check = () => {
    if (!answer) return;
    setChecked(true);
    if (correct) setMastered(true);
    onAttempt(item, answer, correct, attempt, Date.now() - (shownAt.current ?? Date.now()));
  };

  const tryAnother = () => {
    setItemIndex((itemIndex + 1) % items.length);
    setAnswer(null);
    setChecked(false);
    setAttempt(attempt + 1);
    shownAt.current = Date.now();
  };

  return <section className={`question-block ${required ? "required-action" : "evidence-action"}`}>
    <div className="action-heading"><p className="question-label">{required ? "Mastery action" : "Learner action"} · {item.typeLabel}</p><span>Type {itemIndex + 1} of {items.length}</span></div>
    {attempt > 1 && <p className="selection-reason"><strong>Same step, new approach.</strong> LEAP selected a different predefined question type after the previous response.</p>}
    <h4>{item.prompt}</h4>
    <div className="answers">{item.options.map((option) => <button disabled={mastered || checked} className={answer === option ? "answer selected" : "answer"} onClick={() => setAnswer(option)} key={option}>{option}</button>)}</div>
    <button className="check-button" disabled={!answer || mastered || checked} onClick={check}>{mastered ? "Mastered" : checked ? "Answer recorded" : "Check answer"}</button>
    {checked && <p className={correct ? "feedback correct" : "feedback incorrect"}>{correct ? `Correct. ${item.explanation}` : `Not yet. ${item.explanation}`}</p>}
    {checked && !correct && <div className="same-step-plan"><strong>Re-plan this same step</strong><p>LEAP identified <code>{item.misconception}</code>. Stay here and approach the concept through another question format.</p><button className="alternate-button" onClick={tryAnother}>Try a different question type →</button></div>}
  </section>;
}
