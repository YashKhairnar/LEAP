"use client";

import { useEffect, useState } from "react";
import LessonAnimation, { useStepPlayer } from "@/features/learning/components/lesson-animations/lesson-animation";
import { DIGIT_SEVEN_PIXELS } from "@/features/learning/components/digit-matrix-example";

// The same real row the CNN layers animation uses: digit_01651 from images.csv, labeled 7.
const PIXELS = DIGIT_SEVEN_PIXELS.flat();

// In the flat row the 64 values wrap onto 4 lines of 16; in the image they sit in 8 rows of 8.
const flatPosition = (index: number) => ({ left: (index % 16) * 6.25, top: 25 + Math.floor(index / 16) * 12.5 });
const gridPosition = (index: number) => ({ left: 25 + (index % 8) * 6.25, top: Math.floor(index / 8) * 12.5 });

const CAPTIONS = [
  "One row of images.csv: the label 7, then 64 brightness values from 0 (black) to 16 (white). As a flat row, nothing says which pixels sit next to each other.",
  "reshape(-1, 1, 8, 8) cuts the 64 values into 8 groups of 8. Each group becomes one row of the picture, top to bottom.",
  "Shade each value by its brightness and the handwritten 7 appears: the top bar, then the diagonal stroke.",
  "This happens to every row. All 5,620 images stack up into one array of shape (5620, 1, 8, 8): images, channels, rows, columns. The labels stay in a separate array, in the same order.",
];

export default function ReshapeAnimation() {
  const player = useStepPlayer([2600, 3600, 2200]);
  const { step, reducedMotion } = player;
  const [rows, setRows] = useState(0);

  useEffect(() => {
    if (step !== 1 || reducedMotion) return;
    const timer = window.setInterval(() => setRows((value) => Math.min(8, value + 1)), 380);
    return () => { window.clearInterval(timer); setRows(0); };
  }, [step, reducedMotion]);

  const placedRows = step >= 2 ? 8 : step === 1 ? rows : 0;
  const shape = step >= 3 ? "(5620, 1, 8, 8)" : placedRows === 8 ? "(1, 8, 8)" : "64 values";

  return <LessonAnimation
    title="Reshape a row into an image"
    summary="Animation: one row of 64 brightness values from images.csv is cut into 8 rows of 8, forming an 8 by 8 grid. Shaded by brightness, the grid shows a handwritten 7. All 5,620 rows stack into an array of shape 5620, 1, 8, 8."
    caption={CAPTIONS[step]}
    player={player}
  >
    <div className="reshape-anim">
      <div className="reshape-anim-meta">
        <span className="reshape-anim-label">label <strong>7</strong></span>
        <span className="cnn-anim-shape reshape-anim-shape">{shape}</span>
      </div>
      <div className={`reshape-anim-board${step >= 3 ? " is-stacked" : ""}`}>
        {PIXELS.map((value, index) => {
          const row = Math.floor(index / 8);
          const placed = row < placedRows;
          const { left, top } = placed ? gridPosition(index) : flatPosition(index);
          const brightness = Math.round((value / 16) * 255);
          return <span
            key={index}
            className={`reshape-anim-cell${row % 2 ? " is-odd" : ""}${step >= 2 ? " is-shaded" : ""}`}
            style={{
              left: `${left}%`,
              top: `${top}%`,
              transitionDelay: step === 1 ? `${(index % 8) * 25}ms` : "0ms",
              ...(step >= 2 ? { background: `rgb(${brightness}, ${brightness}, ${brightness})`, color: value >= 8 ? "#111" : "#fff" } : {}),
            }}
          >{value}</span>;
        })}
      </div>
      <p className="reshape-anim-note">{step >= 1 ? "1 channel (grayscale) × 8 rows × 8 columns" : "A flat row of 64 numbers, wrapped to fit"}</p>
    </div>
  </LessonAnimation>;
}
