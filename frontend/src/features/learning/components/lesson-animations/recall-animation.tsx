"use client";

import { useState } from "react";
import LessonAnimation, { useStepPlayer } from "@/features/learning/components/lesson-animations/lesson-animation";

type Review = { label: "negative" | "positive"; correct: boolean };

// "This model" scales the real results down to 60 reviews: 241/300 negative and
// 259/300 positive correct become 24/30 and 26/30.
const SCENARIOS = {
  model: {
    button: "This model",
    reviews: [...build("negative", 30, 24), ...build("positive", 30, 26)],
    captions: [
      "60 test reviews, scaled down from the real 600. Each dot is one review.",
      "Mark each prediction. Filled dots are right; hollow dots with a cross are wrong. 50 of 60 are right: accuracy 83%, the same as the real 500 of 600.",
      "Now group the dots by their true label. Negative: 24 of 30 caught, recall 0.80. Positive: 26 of 30, recall 0.87. The real model scores 0.80 and 0.86.",
      "Same accuracy, but the per-label view shows this model misses negative reviews more often.",
    ],
  },
  lopsided: {
    button: "A lopsided test set",
    reviews: [...build("negative", 3, 0), ...build("positive", 57, 57)],
    captions: [
      "A different test set: 57 positive reviews and only 3 negative ones.",
      "A lazy model that always says positive gets 57 of 60 right: 95% accuracy.",
      "Grouped by true label: positive recall is 57 of 57 = 1.00, but negative recall is 0 of 3 = 0.",
      "Accuracy looked great, yet the model never catches a single negative review. That's why you check recall for each label.",
    ],
  },
};

function build(label: Review["label"], count: number, correct: number): Review[] {
  return Array.from({ length: count }, (_, index) => ({ label, correct: index < correct }));
}

// A fixed shuffle so the mixed view looks mixed but is the same every time.
function mixed(reviews: Review[]): Review[] {
  return reviews.map((review, index) => ({ review, key: (index * 37) % reviews.length })).sort((a, b) => a.key - b.key).map(({ review }) => review);
}

export default function RecallAnimation() {
  const player = useStepPlayer([1400, 2600, 2600]);
  const { step, play } = player;
  const [scenario, setScenario] = useState<keyof typeof SCENARIOS>("model");
  const { reviews, captions } = SCENARIOS[scenario];
  const correct = reviews.filter((review) => review.correct).length;
  const dot = (review: Review, index: number) => <span key={index} className={`recall-anim-dot${step >= 1 ? (review.correct ? " is-right" : " is-wrong") : ""}`} />;
  const group = (label: Review["label"]) => {
    const members = reviews.filter((review) => review.label === label);
    const caught = members.filter((review) => review.correct).length;
    return <div className="recall-anim-group">
      <div className="recall-anim-group-head"><strong>Truly {label}</strong><span>recall {(caught / members.length).toFixed(2)} · {caught} of {members.length}</span></div>
      <div className="recall-anim-dots">{members.map(dot)}</div>
    </div>;
  };

  return <LessonAnimation
    title="Accuracy vs recall for each label"
    summary={scenario === "model"
      ? "Animation: 60 test reviews are marked right or wrong, giving 83% accuracy, then grouped by true label, showing recall 0.80 for negative and 0.87 for positive."
      : "Animation: on a test set of 57 positive and 3 negative reviews, a model that always says positive reaches 95% accuracy but has a negative recall of 0."}
    caption={captions[step]}
    player={player}
  >
    <div className="recall-anim">
      <div className="weights-anim-tabs" role="group" aria-label="Choose a test set">
        {(Object.keys(SCENARIOS) as (keyof typeof SCENARIOS)[]).map((key) => <button key={key} type="button" aria-pressed={key === scenario} onClick={() => { setScenario(key); play(); }}>{SCENARIOS[key].button}</button>)}
      </div>
      {step < 2
        ? <div className="recall-anim-mixed">
            <div className="recall-anim-dots">{mixed(reviews).map(dot)}</div>
            <p className={`recall-anim-accuracy${step >= 1 ? " is-on" : ""}`}>Accuracy <strong>{Math.round((correct / reviews.length) * 100)}%</strong> · {correct} of {reviews.length} right</p>
          </div>
        : <div className="recall-anim-split">{group("negative")}{group("positive")}</div>}
      <div className="recall-anim-key" aria-hidden="true"><span className="recall-anim-dot is-right" /> right <span className="recall-anim-dot is-wrong" /> wrong</div>
    </div>
  </LessonAnimation>;
}
