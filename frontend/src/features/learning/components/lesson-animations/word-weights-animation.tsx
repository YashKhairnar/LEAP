"use client";

import { useState } from "react";
import LessonAnimation, { useStepPlayer } from "@/features/learning/components/lesson-animations/lesson-animation";

// Real values from the trained lesson model: each word's TF-IDF value, its learned weight,
// and their product. The model's starting point (intercept) is −0.15.
const START = -0.15;
type Contribution = [word: string, value: number, weight: number, product: number];
const REVIEWS: { text: string; score: number; label: "positive" | "negative"; sure: number; note: string; words: Contribution[] }[] = [
  {
    text: "I loved it.", score: 1.61, label: "positive", sure: 83,
    note: "'loved' does almost all the work. The prediction is right.",
    words: [["loved", 0.92, 1.81, 1.66], ["it", 0.39, 0.25, 0.10]],
  },
  {
    text: "The food was not bad at all.", score: -4.26, label: "negative", sure: 99,
    note: "Wrong! 'not' and 'bad' each push hard towards negative. The model scores words one at a time, so it can't see that together they mean 'good'.",
    words: [["not", 0.34, -4.60, -1.56], ["bad", 0.45, -3.42, -1.55], ["at", 0.42, -1.78, -0.75], ["food", 0.44, -0.51, -0.23], ["was", 0.29, -0.44, -0.13], ["all", 0.43, 0.23, 0.10], ["the", 0.19, 0.05, 0.01]],
  },
  {
    text: "The mic is great.", score: 2.01, label: "positive", sure: 88,
    note: "'mic' has the biggest TF-IDF value but a learned weight of 0: it says nothing about sentiment. 'great' decides it.",
    words: [["great", 0.41, 4.92, 2.00], ["is", 0.28, 0.57, 0.16], ["the", 0.20, 0.05, 0.01], ["mic", 0.85, 0.00, 0.00]],
  },
];
const RANGE = 5;
const signed = (value: number) => `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toFixed(2)}`;
const toPercent = (score: number) => ((Math.max(-RANGE, Math.min(RANGE, score)) + RANGE) / (2 * RANGE)) * 100;

export default function WordWeightsAnimation() {
  const player = useStepPlayer([1500, 2600, 1800]);
  const { step, play } = player;
  const [selected, setSelected] = useState(0);
  const review = REVIEWS[selected];
  const captions = [
    `Every prediction starts from the model's starting point, ${signed(START)}, just below 0.`,
    "Each word adds its TF-IDF value × its learned weight. Blue pushes towards positive; orange pushes towards negative.",
    `Add everything up: the total is ${signed(review.score)}. Above 0 means positive, below 0 means negative.`,
    `Prediction: ${review.label} (${review.sure}% sure). ${review.note}`,
  ];
  const needle = step >= 2 ? review.score : START;

  return <LessonAnimation
    title="How a prediction adds up"
    summary={`Animation: for the review "${review.text}", each word's TF-IDF value times its weight is added to a starting point of −0.15, giving ${signed(review.score)}, so the prediction is ${review.label}.`}
    caption={captions[step]}
    player={player}
  >
    <div className="weights-anim">
      <div className="weights-anim-tabs" role="group" aria-label="Choose a review">
        {REVIEWS.map((item, index) => <button key={item.text} type="button" aria-pressed={index === selected} onClick={() => { setSelected(index); play(); }}>{item.text}</button>)}
      </div>
      <ol className={`weights-anim-words${step >= 1 ? " is-on" : ""}`}>
        {review.words.map(([word, value, weight, product], index) => <li key={word} className={product > 0 ? "is-up" : product < 0 ? "is-down" : "is-flat"} style={{ transitionDelay: `${index * 160}ms` }}>
          <strong>{word}</strong>
          <span>{value.toFixed(2)} × {signed(weight)}</span>
          <em>{signed(product)}</em>
        </li>)}
      </ol>
      <div className="weights-anim-scale">
        <div className="weights-anim-track">
          <span className="weights-anim-zero" />
          <span className={`weights-anim-needle${step >= 3 ? ` is-${review.label}` : ""}`} style={{ left: `${toPercent(needle)}%` }}>
            <em>{signed(needle)}</em>
          </span>
        </div>
        <div className="weights-anim-ends"><span>← negative</span><span>0</span><span>positive →</span></div>
      </div>
    </div>
  </LessonAnimation>;
}
