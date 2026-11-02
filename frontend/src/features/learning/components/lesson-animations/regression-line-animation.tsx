"use client";

import { useEffect, useState } from "react";
import LessonAnimation, { useStepPlayer } from "@/features/learning/components/lesson-animations/lesson-animation";

// 14 real sales from backend/datasets/ames_housing_v2.csv: [square feet, price].
const SALES: [number, number][] = [
  [936, 140000], [1053, 145500], [1152, 61500], [1262, 185000], [1296, 127500], [1347, 143000], [1352, 208900],
  [1361, 89000], [1430, 168000], [1566, 150000], [1656, 135000], [1733, 225000], [2110, 205000], [2610, 303477],
];

const meanX = SALES.reduce((sum, [x]) => sum + x, 0) / SALES.length;
const meanY = SALES.reduce((sum, [, y]) => sum + y, 0) / SALES.length;
const SLOPE = SALES.reduce((sum, [x, y]) => sum + (x - meanX) * (y - meanY), 0) / SALES.reduce((sum, [x]) => sum + (x - meanX) ** 2, 0);
const INTERCEPT = meanY - SLOPE * meanX;
const predict = (x: number) => INTERCEPT + SLOPE * x;
const ERRORS = SALES.map(([x, y]) => predict(x) - y);
const MAE = ERRORS.reduce((sum, error) => sum + Math.abs(error), 0) / ERRORS.length;
const LARGEST = Math.max(...ERRORS.map(Math.abs));

const X0 = 800, X1 = 2700, Y0 = 40000, Y1 = 320000;
const px = (x: number) => 64 + ((x - X0) / (X1 - X0)) * 516;
const py = (y: number) => 290 - ((y - Y0) / (Y1 - Y0)) * 270;
const money = (value: number) => `$${Math.round(value).toLocaleString("en-US")}`;

const FIT_CAPTIONS = [
  "Each dot is a real sale from Ames: its size and the price it sold for. 14 of the 2,930 sales are shown.",
  "A first guess: predict the average price for every house. The dashed lines are its errors, and many are large.",
  "fit moves the line to the slope and starting point that make the errors as small as possible overall.",
  `The fitted line: price ≈ ${money(INTERCEPT)} + ${money(SLOPE)} × square feet. The real model does this with all four features at once and with scaled inputs, so it learns four coefficients per spread instead of one per square foot.`,
];
const ERROR_CAPTIONS = [
  "The fitted line with the same 14 real sales.",
  "Each dashed line is one house's error, predicted − actual. Orange dashes: the model guessed too high. Blue dots: too low.",
  "Drop the signs. Every error becomes a positive size, so the too-high and too-low ones can't cancel out.",
  `Average the sizes: MAE ≈ ${money(MAE)} for these 14 houses. On average, the predictions miss by about that much; some miss by far more.`,
];

export default function RegressionLineAnimation({ mode }: { mode: "fit" | "errors" }) {
  const player = useStepPlayer(mode === "fit" ? [1400, 2400, 2000] : [1400, 2600, 2200]);
  const { step, reducedMotion } = player;
  const [progress, setProgress] = useState(0);

  // Ease the line from the flat first guess to the fitted line during step 2 of "fit".
  useEffect(() => {
    if (mode !== "fit" || step !== 2 || reducedMotion) return;
    let frame = 0;
    const started = performance.now();
    const tick = (time: number) => {
      const t = Math.min(1, (time - started) / 1500);
      setProgress(1 - Math.pow(1 - t, 3));
      if (t < 1) frame = window.requestAnimationFrame(tick);
    };
    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [mode, step, reducedMotion]);

  const blend = mode === "errors" || step >= 3 ? 1 : step === 2 ? progress : 0;
  const lineAt = (x: number) => (1 - blend) * meanY + blend * predict(x);
  const showLine = mode === "errors" || step >= 1;
  const showErrors = mode === "fit" ? step >= 1 && step <= 2 : step >= 1;

  return <LessonAnimation
    title={mode === "fit" ? "Watch the line being fitted" : "From errors to MAE"}
    summary={mode === "fit"
      ? "Animation: 14 real house sales are plotted by size and price, a flat line at the average price is replaced by the best-fitting sloped line."
      : "Animation: errors between 14 real sales and the fitted line are drawn, their signs are dropped, and their average gives the mean absolute error."}
    caption={(mode === "fit" ? FIT_CAPTIONS : ERROR_CAPTIONS)[step]}
    player={player}
  >
    <div className={`reg-anim${mode === "errors" && step >= 2 ? " has-bars" : ""}`}>
      <svg className="reg-anim-chart" viewBox="0 0 600 320" role="presentation">
        <line className="reg-anim-axis" x1="64" y1="290" x2="580" y2="290" />
        <line className="reg-anim-axis" x1="64" y1="20" x2="64" y2="290" />
        {[1000, 1500, 2000, 2500].map((x) => <text key={x} className="reg-anim-tick" x={px(x)} y="308" textAnchor="middle">{x.toLocaleString("en-US")}</text>)}
        {[100000, 200000, 300000].map((y) => <text key={y} className="reg-anim-tick" x="58" y={py(y) + 4} textAnchor="end">{`$${y / 1000}k`}</text>)}
        <text className="reg-anim-axis-label" x="322" y="320" textAnchor="middle">square feet</text>
        {showErrors && SALES.map(([x, y], index) => {
          const tooHigh = lineAt(x) > y;
          return <line key={`e${index}`} className={`reg-anim-error ${tooHigh ? "is-high" : "is-low"}`} x1={px(x)} x2={px(x)} y1={py(y)} y2={py(lineAt(x))} />;
        })}
        {showLine && <line className="reg-anim-line" x1={px(X0)} y1={py(lineAt(X0))} x2={px(X1)} y2={py(lineAt(X1))} />}
        {SALES.map(([x, y], index) => <circle key={index} className="reg-anim-dot" cx={px(x)} cy={py(y)} r="6" style={{ transitionDelay: `${index * 60}ms` }} />)}
        {mode === "fit" && step >= 3 && <text className="reg-anim-equation" x="80" y="40">{`price ≈ ${money(INTERCEPT)} + ${money(SLOPE)} × sq ft`}</text>}
      </svg>
      {mode === "errors" && <div className={`reg-anim-bars${step >= 2 ? " is-on" : ""}`} aria-hidden="true">
        <span className="reg-anim-bars-title">Size of each error</span>
        <div className="reg-anim-bars-plot">
          {[...ERRORS].sort((a, b) => Math.abs(b) - Math.abs(a)).map((error, index) => <span key={index} className={error > 0 ? "is-high" : "is-low"} style={{ height: step >= 2 ? `${(Math.abs(error) / LARGEST) * 100}%` : "0%", transitionDelay: `${index * 70}ms` }} />)}
          {step >= 3 && <span className="reg-anim-mae" style={{ bottom: `${(MAE / LARGEST) * 100}%` }}><em>{`MAE ≈ ${money(MAE)}`}</em></span>}
        </div>
      </div>}
    </div>
  </LessonAnimation>;
}
