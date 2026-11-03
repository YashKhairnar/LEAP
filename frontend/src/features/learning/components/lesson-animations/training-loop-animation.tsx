"use client";

import { useEffect, useState } from "react";
import LessonAnimation, { useStepPlayer } from "@/features/learning/components/lesson-animations/lesson-animation";

// Real values from one run of the lesson's training cell: the loss for each of the 36 batches,
// and the share of each batch the model got right just after that batch's update.
const LOSSES = [2.34, 2.3, 2.19, 2.2, 2.1, 2.03, 1.95, 1.85, 1.81, 1.68, 1.64, 1.5, 1.38, 1.24, 1.21, 1.06, 1.02, 0.93, 0.9, 0.73, 0.71, 0.62, 0.66, 0.52, 0.61, 0.45, 0.48, 0.35, 0.35, 0.43, 0.42, 0.45, 0.32, 0.19, 0.3, 0.37];
const CORRECT = [0.14, 0.16, 0.47, 0.28, 0.41, 0.52, 0.55, 0.59, 0.57, 0.72, 0.74, 0.83, 0.78, 0.84, 0.85, 0.9, 0.86, 0.89, 0.84, 0.91, 0.9, 0.85, 0.86, 0.89, 0.84, 0.91, 0.93, 0.95, 0.91, 0.88, 0.86, 0.9, 0.92, 0.98, 0.91, 0.94];

const STEPS = [
  { code: "optimizer.zero_grad()", text: "Clear the last batch's gradients" },
  { code: "model(images_batch / 16.0)", text: "Score 128 images" },
  { code: "loss_fn(…, labels_batch)", text: "Measure how wrong" },
  { code: "loss.backward()", text: "Work out each weight's nudge" },
  { code: "optimizer.step()", text: "Nudge every weight" },
];

const X0 = 44, X1 = 584, Y0 = 16, Y1 = 176;
const px = (batch: number) => X0 + (batch / 35) * (X1 - X0);
const py = (loss: number) => Y1 - (loss / 2.5) * (Y1 - Y0);

const CAPTIONS = [
  "Training repeats the same five lines for every batch of 128 images. The weights start random.",
  "Batch 1: the model scores the images, the loss measures how wrong it was (2.34, about what random guessing gets), backward() works out a nudge for all 2,730 weights, and step() applies it.",
  "Then again for batch 2, 3 and so on: 36 batches make one pass over the 4,496 training images. Each nudge is small, but the loss keeps falling.",
  "After batch 36 the loss is 0.37, the value the code prints, and the model gets 94% of that batch right, up from 14% on batch 1. The line wobbles because every batch holds different images.",
];

export default function TrainingLoopAnimation() {
  const player = useStepPlayer([1600, 4200, 4400]);
  const { step, reducedMotion } = player;
  const [tick, setTick] = useState(0);

  // Step 1 walks the five lines once for batch 1; step 2 runs batches 2–36 quickly.
  useEffect(() => {
    if ((step !== 1 && step !== 2) || reducedMotion) return;
    const timer = window.setInterval(() => setTick((value) => value + 1), step === 1 ? 760 : 115);
    return () => { window.clearInterval(timer); setTick(0); };
  }, [step, reducedMotion]);

  const batch = step <= 1 ? 0 : step === 2 ? Math.min(35, 1 + tick) : 35;
  const active = step === 1 ? Math.min(4, tick) : step === 2 ? tick % 5 : -1;
  const plotted = step === 0 ? 0 : step === 1 ? (tick >= 2 ? 1 : 0) : batch + 1;
  const path = LOSSES.slice(0, plotted).map((loss, index) => `${index ? "L" : "M"}${px(index)},${py(loss)}`).join(" ");
  const shown = plotted ? plotted - 1 : 0;

  return <LessonAnimation
    title="Watch one pass of training"
    summary="Animation: the five lines of the training loop run for each of 36 batches. A chart plots the real loss per batch, falling from 2.34 on batch 1 to 0.37 on batch 36, while the share of the batch classified correctly rises from 14% to 94%."
    caption={CAPTIONS[step]}
    player={player}
  >
    <div className="train-anim">
      <ol className="train-anim-loop">
        {STEPS.map((item, index) => <li key={item.code} className={index === active ? "is-active" : ""}>
          <code>{item.code}</code>
          <span>{item.text}</span>
        </li>)}
      </ol>
      <div className="train-anim-chart">
        <div className="train-anim-stats">
          <span>Batch <strong>{step === 0 ? "–" : batch + 1}</strong> of 36</span>
          <span>Loss <strong>{plotted ? LOSSES[shown].toFixed(2) : "–"}</strong></span>
          <span>Right <strong>{plotted ? `${Math.round(CORRECT[shown] * 100)}%` : "–"}</strong></span>
        </div>
        <svg viewBox="0 0 600 226" role="presentation">
          <line className="reg-anim-axis" x1={X0} x2={X1} y1={Y1} y2={Y1} />
          <line className="reg-anim-axis" x1={X0} x2={X0} y1={Y0} y2={Y1} />
          {[0, 1, 2].map((loss) => <text key={loss} className="reg-anim-tick" x={X0 - 10} y={py(loss) + 4} textAnchor="end">{loss}</text>)}
          {[1, 12, 24, 36].map((value) => <text key={value} className="reg-anim-tick" x={px(value - 1)} y={Y1 + 20} textAnchor="middle">{value}</text>)}
          <text className="reg-anim-axis-label" x={(X0 + X1) / 2} y={Y1 + 44} textAnchor="middle">batch</text>
          <line className="train-anim-guess" x1={X0} x2={X1} y1={py(2.3)} y2={py(2.3)} />
          <text className="train-anim-guess-label" x={X1} y={py(2.3) - 6} textAnchor="end">random guessing ≈ 2.3</text>
          {path && <path className="train-anim-line" d={path} />}
          {plotted > 0 && <circle className="train-anim-dot" r={6} cx={px(shown)} cy={py(LOSSES[shown])} />}
        </svg>
      </div>
    </div>
  </LessonAnimation>;
}
