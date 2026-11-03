"use client";

import LessonAnimation, { useStepPlayer } from "@/features/learning/components/lesson-animations/lesson-animation";

// 100 dots, each standing for 30 of the 3,000 reviews (1,500 positive, 1,500 negative), shuffled.
const DOTS = Array.from({ length: 100 }, (_, index) => ({ positive: (index * 37) % 100 < 50, order: index }));
// Which 10 positive and 10 negative dots go to the test set (20% of each class).
const positives = DOTS.filter((dot) => dot.positive);
const negatives = DOTS.filter((dot) => !dot.positive);
const TEST = new Set([...positives.filter((_, index) => index % 5 === 2), ...negatives.filter((_, index) => index % 5 === 4)].map((dot) => dot.order));

// Positive reviews in a 600-review test set from train_test_split without stratify, random_state 0 to 9.
const ZONES = { all: { x: 0, w: 100, cols: 20 }, train: { x: 0, w: 70, cols: 18 }, test: { x: 74, w: 26, cols: 4 } };

const UNSTRATIFIED = [305, 313, 307, 297, 297, 299, 302, 311, 293, 312];

const CAPTIONS = [
  "All 3,000 reviews: 1,500 positive and 1,500 negative. Each dot here stands for 30 reviews.",
  "stratify=df[\"sentiment\"] splits each class separately. First, 20% of the positive reviews, 300 of them, go to the test set.",
  "Then 20% of the negative reviews, also 300. Test: 300 positive + 300 negative. Training: 1,200 + 1,200. Both keep the 50/50 mix.",
  "Without stratify, the mix depends on luck. Over 10 random seeds, the test set got between 293 and 313 positive reviews. Here that's a small wobble, but with lopsided data, say 90% positive, a random split can leave very few negatives to test on.",
];

export default function StratifyAnimation() {
  const player = useStepPlayer([1600, 2600, 3000]);
  const { step } = player;

  // Dot positions are percentages of the whole figure; the zones sit side by side once split.
  const place = (dot: typeof DOTS[number]) => {
    const moved = TEST.has(dot.order) && (step >= 2 || (step === 1 && dot.positive));
    const [zone, index] = step === 0
      ? ["all", dot.order] as const
      : moved
        ? ["test", [...TEST].filter((order) => order < dot.order).length] as const
        : ["train", DOTS.filter((other) => !(TEST.has(other.order) && (step >= 2 || other.positive)) && other.order < dot.order).length] as const;
    const { x, w, cols } = ZONES[zone];
    return { left: x + ((index % cols) + 0.5) / cols * w, top: 14 + Math.floor(index / cols) * 18 };
  };
  const count = (positive: boolean, inTest: boolean) => DOTS.filter((dot) => dot.positive === positive
    && (TEST.has(dot.order) && (step >= 2 || (step === 1 && dot.positive))) === inTest).length * 30;
  const label = (inTest: boolean) => `${count(true, inTest).toLocaleString("en-US")} pos · ${count(false, inTest).toLocaleString("en-US")} neg`;

  return <LessonAnimation
    title="Split each class separately"
    summary="Animation: 3,000 reviews, half positive and half negative, are split 80/20. With stratify, 300 positive and 300 negative reviews go to the test set, leaving 1,200 of each for training. Without stratify, ten random seeds gave test sets with 293 to 313 positive reviews."
    caption={CAPTIONS[step]}
    player={player}
  >
    {step < 3 ? <>
      <div className="split-anim">
        <div className={`split-anim-zone is-all${step === 0 ? " is-on" : ""}`} />
        <div className={`split-anim-zone is-train${step >= 1 ? " is-on" : ""}`} />
        <div className={`split-anim-zone is-test${step >= 1 ? " is-on" : ""}`} />
        {DOTS.map((dot) => {
          const { left, top } = place(dot);
          return <span key={dot.order} className={`split-anim-dot ${dot.positive ? "is-positive" : "is-negative"}`} style={{ left: `${left}%`, top: `${top}%` }} />;
        })}
      </div>
      <div className="split-anim-labels">
        {step === 0
          ? <span>All reviews<em>1,500 pos · 1,500 neg</em></span>
          : <><span className="is-train">Training<em>{label(false)}</em></span><span className="is-test">Test<em>{label(true)}</em></span></>}
      </div>
    </> : <div className="split-anim-luck">
      <span className="split-anim-zone-label">Positive reviews in a 600-review test set, without stratify</span>
      <div className="split-anim-luck-plot">
        <span className="split-anim-luck-target" />
        {UNSTRATIFIED.map((count, seed) => <div key={seed} className={count >= 300 ? "is-over" : "is-under"}>
          <span style={{ height: `${(Math.abs(count - 300) / 15) * 50}%` }}><strong>{count}</strong></span>
        </div>)}
      </div>
      <span className="split-anim-luck-axis">random_state 0 → 9 · the line is 300, exactly half</span>
    </div>}
    {step < 3 && <p className="split-anim-key">
      <span><i className="split-anim-dot is-positive is-key" />positive</span>
      <span><i className="split-anim-dot is-negative is-key" />negative</span>
    </p>}
  </LessonAnimation>;
}
