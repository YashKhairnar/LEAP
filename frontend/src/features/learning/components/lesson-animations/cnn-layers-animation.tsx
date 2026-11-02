"use client";

import { useEffect, useState } from "react";
import LessonAnimation, { useStepPlayer } from "@/features/learning/components/lesson-animations/lesson-animation";
import { DIGIT_SEVEN_PIXELS } from "@/features/learning/components/digit-matrix-example";

// An example horizontal-edge filter: it responds where a bright row sits above a dark one,
// such as the underside of the 7's top bar. The model's real filters are learned.
const FILTER = [[1, 1, 1], [0, 0, 0], [-1, -1, -1]];
const SCORES = [-1.2, 0.3, 0.1, 0.8, -0.5, 0.2, -0.9, 3.4, 0.6, 0.4];

const image = DIGIT_SEVEN_PIXELS.map((row) => row.map((value) => value / 16));
const featureMap = image.map((row, y) => row.map((_, x) => {
  let total = 0;
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
    total += (image[y + dy]?.[x + dx] ?? 0) * FILTER[dy + 1][dx + 1];
  }
  return Math.max(0, total); // ReLU
}));
const pooled = [0, 1, 2, 3].map((y) => [0, 1, 2, 3].map((x) => Math.max(
  featureMap[2 * y][2 * x], featureMap[2 * y][2 * x + 1], featureMap[2 * y + 1][2 * x], featureMap[2 * y + 1][2 * x + 1],
)));
const peak = Math.max(...featureMap.flat(), 0.001);
const shade = (value: number) => `rgb(${Math.round(255 - value * 200)}, ${Math.round(255 - value * 150)}, 255)`;

const CAPTIONS = [
  "The input is one 8 × 8 image of a 7: shape 1 × 8 × 8.",
  "A 3 × 3 filter slides over every position. This one responds where bright sits above dark, like the underside of the 7's top bar. Each position becomes one number in a feature map. Conv2d has 16 filters, so 16 maps: 16 × 8 × 8.",
  "MaxPool2d(2) keeps the largest value in each 2 × 2 block, so every 8 × 8 map becomes 4 × 4: 16 × 4 × 4.",
  "Flatten lines the values up into one list: 16 values per map × 16 maps = 256 numbers.",
  "Linear(256, 10) turns those 256 numbers into 10 scores, one per digit. The highest score, for 7, is the prediction. The filter and scores here are examples; the real ones are learned in training.",
];

export default function CnnLayersAnimation() {
  const player = useStepPlayer([1000, 4000, 2200, 2200]);
  const { step, reducedMotion } = player;
  const [position, setPosition] = useState(0);

  useEffect(() => {
    if (step !== 1 || reducedMotion) return;
    const timer = window.setInterval(() => setPosition((value) => Math.min(64, value + 1)), 56);
    return () => { window.clearInterval(timer); setPosition(0); };
  }, [step, reducedMotion]);

  const filled = step >= 2 ? 64 : step === 1 ? position : 0;
  const windowY = Math.floor(Math.min(filled, 63) / 8);
  const windowX = Math.min(filled, 63) % 8;
  const panel = (index: number) => `cnn-anim-panel${step >= index ? " is-on" : ""}${step === index ? " is-current" : ""}`;

  return <LessonAnimation
    title="Follow one image through the network"
    summary="Animation: a 3 by 3 filter slides over an 8 by 8 image of a 7, the feature map is pooled to 4 by 4, flattened to 256 numbers, and turned into 10 digit scores with 7 highest."
    caption={CAPTIONS[step]}
    player={player}
  >
    <div className="cnn-anim">
      <div className={panel(0)}>
        <span className="cnn-anim-shape">1 × 8 × 8</span>
        <div className="cnn-anim-grid is-8">
          {image.flatMap((row, y) => row.map((value, x) => <span key={`${y}-${x}`} style={{ background: `rgb(${Math.round(value * 255)}, ${Math.round(value * 255)}, ${Math.round(value * 255)})` }} />))}
          {step === 1 && <span className="cnn-anim-window" style={{ left: `${(windowX - 1) * 12.5}%`, top: `${(windowY - 1) * 12.5}%` }} />}
        </div>
        <span className="cnn-anim-label">Input image</span>
      </div>
      <span className="cnn-anim-arrow" aria-hidden="true">→</span>
      <div className={panel(1)}>
        <span className="cnn-anim-shape">16 × 8 × 8</span>
        <div className="cnn-anim-grid is-8">
          {featureMap.flatMap((row, y) => row.map((value, x) => <span key={`${y}-${x}`} style={{ background: y * 8 + x < filled ? shade(value / peak) : "#f1f4f8" }} />))}
        </div>
        <span className="cnn-anim-label">Conv2d + ReLU (map 1 of 16)</span>
      </div>
      <span className="cnn-anim-arrow" aria-hidden="true">→</span>
      <div className={panel(2)}>
        <span className="cnn-anim-shape">16 × 4 × 4</span>
        <div className="cnn-anim-grid is-4">
          {pooled.flatMap((row, y) => row.map((value, x) => <span key={`${y}-${x}`} style={{ background: step >= 2 ? shade(value / peak) : "#f1f4f8" }} />))}
        </div>
        <span className="cnn-anim-label">MaxPool2d(2)</span>
      </div>
      <span className="cnn-anim-arrow" aria-hidden="true">→</span>
      <div className={panel(3)}>
        <span className="cnn-anim-shape">256</span>
        <div className="cnn-anim-strip">
          {pooled.flat().map((value, index) => <span key={index} style={{ background: step >= 3 ? shade(value / peak) : "#f1f4f8", transitionDelay: `${index * 40}ms` }} />)}
        </div>
        <span className="cnn-anim-label">Flatten: 16 values × 16 maps</span>
      </div>
      <span className="cnn-anim-arrow" aria-hidden="true">→</span>
      <div className={panel(4)}>
        <span className="cnn-anim-shape">10</span>
        <div className="cnn-anim-scores">
          {SCORES.map((score, digit) => <div key={digit} className={step >= 4 && digit === 7 ? "is-top" : ""}>
            <span style={{ height: step >= 4 ? `${Math.max(4, ((score + 1.5) / 5) * 100)}%` : "4%" }} />
            <em>{digit}</em>
          </div>)}
        </div>
        <span className="cnn-anim-label">Linear: one score per digit</span>
      </div>
    </div>
  </LessonAnimation>;
}
