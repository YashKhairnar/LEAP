"use client";

import LessonAnimation, { useStepPlayer } from "@/features/learning/components/lesson-animations/lesson-animation";

// The first 40 training houses from the lesson split: [square feet, age in years].
const HOUSES: [number, number][] = [
  [1370, 33], [2126, 42], [1224, 45], [1040, 60], [1701, 89], [2060, 19], [1976, 8], [1375, 52], [2380, 42], [1602, 2],
  [974, 16], [2726, 21], [1374, 3], [1450, 1], [1032, 71], [1080, 3], [1062, 55], [1778, 1], [995, 84], [1253, 48],
  [1560, 53], [1072, 1], [1523, 60], [1725, 7], [616, 85], [848, 2], [1782, 5], [1316, 1], [1144, 54], [1513, 10],
  [1492, 8], [1281, 82], [1385, 58], [1047, 122], [1222, 0], [1929, 6], [1660, 74], [1143, 2], [1073, 53], [1288, 12],
];
// What StandardScaler learned from all 2,344 training houses.
const FEATURES = [
  { name: "square_feet", unit: "sq ft", mean: 1492.9, spread: 504.5, max: 3000, ticks: [0, 1000, 2000, 3000] },
  { name: "age_years", unit: "years", mean: 37.3, spread: 30.4, max: 130, ticks: [0, 40, 80, 120] },
];

// Plot geometry (SVG units). Raw values fill 40–560; in scaled form 0 sits at ZERO and one spread is UNIT wide.
const LEFT = 40, RIGHT = 560, ZERO = 200, UNIT = 100;
const position = (value: number, feature: typeof FEATURES[number], step: number) => {
  const perUnit = (RIGHT - LEFT) / feature.max;
  if (step <= 1) return LEFT + value * perUnit;
  if (step === 2) return ZERO + (value - feature.mean) * perUnit;
  return ZERO + ((value - feature.mean) / feature.spread) * UNIT;
};
const signed = (value: number, digits = 0) => `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toLocaleString("en-US", { maximumFractionDigits: digits })}`;

const CAPTIONS = [
  "40 real training houses on two features. Square feet run into the thousands and age into the tens, so a step of 1 means something different on each line.",
  "The scaler first learns each feature's average from the training houses: 1,493 sq ft and 37 years.",
  "Subtract the average. Now 0 means \"a typical house\": the highlighted house, 1,370 sq ft and 33 years old, sits at −123 sq ft and −4 years.",
  "Divide by the typical spread, 505 sq ft and 30 years. Both features now use the same scale: 1 means one spread above average. The highlighted house becomes −0.24 and −0.14, the values the code prints.",
];

export default function ScalingAnimation() {
  const player = useStepPlayer([2200, 2400, 2800]);
  const { step } = player;

  return <LessonAnimation
    title="Put features on one scale"
    summary="Animation: 40 real houses on two number lines, square feet and age in years. The training averages, 1,493 square feet and 37 years, are subtracted so 0 means average, then each feature is divided by its spread, 505 square feet and 30 years. The highlighted house, 1,370 square feet and 33 years old, ends at minus 0.24 and minus 0.14."
    caption={CAPTIONS[step]}
    player={player}
  >
    <svg className="scale-anim" viewBox="0 0 600 260" role="presentation">
      {FEATURES.map((feature, row) => {
        const y = 76 + row * 124;
        const ticks = step <= 1
          ? feature.ticks.map((value) => ({ x: position(value, feature, step), label: value.toLocaleString("en-US") }))
          : step === 2
            ? feature.ticks.map((value) => value - feature.ticks[1]).map((offset) => ({ x: position(feature.mean + offset, feature, 2), label: offset === 0 ? "0" : signed(offset) }))
            : [-1, 0, 1, 2, 3].map((z) => ({ x: ZERO + z * UNIT, label: z === 0 ? "0" : signed(z) }));
        const first = HOUSES[0][row];
        const firstLabel = step <= 1 ? `${first.toLocaleString("en-US")}` : step === 2 ? signed(first - feature.mean) : signed((first - feature.mean) / feature.spread, 2);
        return <g key={feature.name}>
          <text className="scale-anim-name" x={LEFT} y={y - 52}>{feature.name}<tspan>{step >= 3 ? " · spreads from average" : ` · ${feature.unit}${step === 2 ? " from average" : ""}`}</tspan></text>
          <line className="scale-anim-axis" x1={20} x2={580} y1={y} y2={y} />
          {ticks.map((tick) => tick.x >= 10 && tick.x <= 590 && <g key={`${step}-${tick.label}`} className="scale-anim-tick">
            <line x1={tick.x} x2={tick.x} y1={y - 4} y2={y + 4} />
            <text x={tick.x} y={y + 22}>{tick.label}</text>
          </g>)}
          {HOUSES.map((house, index) => <circle
            key={index}
            className={`scale-anim-dot${index === 0 ? " is-picked" : ""}`}
            r={index === 0 ? 7 : 5}
            cx={0}
            cy={0}
            style={{ transform: `translate(${Math.min(590, position(house[row], feature, step))}px, ${y - 12 - (index % 3) * 5}px)` }}
          />)}
          <g className={`scale-anim-mean${step >= 1 ? " is-on" : ""}`} style={{ transform: `translateX(${position(feature.mean, feature, step)}px)` }}>
            <line x1={0} x2={0} y1={y - 38} y2={y + 6} />
            <text x={6} y={y - 30}>{step === 1 ? `average ${Math.round(feature.mean).toLocaleString("en-US")}` : step >= 2 ? "average = 0" : ""}</text>
          </g>
          <text className="scale-anim-picked" style={{ transform: `translateX(${position(first, feature, step)}px)` }} x={0} y={y + 40}>{firstLabel}</text>
        </g>;
      })}
    </svg>
  </LessonAnimation>;
}
