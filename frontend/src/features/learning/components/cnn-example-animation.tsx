"use client";

import { useEffect, useRef } from "react";

const DIGIT_ART = [
  "              ",
  "              ",
  "  .########+  ",
  "  .+++++++##  ",
  "         +#.  ",
  "        .##   ",
  "        +#.   ",
  "       .##    ",
  "       +#.    ",
  "      .##     ",
  "      +#+     ",
  "      ##.     ",
  "     .#+      ",
  "              ",
];

const BRIGHTNESS: Record<string, number> = { " ": 0, ".": 0.3, "+": 0.65, "#": 1 };
const DIGIT = DIGIT_ART.map((row) => [...row].map((pixel) => BRIGHTNESS[pixel]));
const FILTERS = [
  [[1, 1, 1], [0, 0, 0], [-1, -1, -1]],
  [[1, 0, -1], [1, 0, -1], [1, 0, -1]],
  [[0, 1, 1], [-1, 0, 1], [-1, -1, 0]],
];
const PROBABILITIES = [0.002, 0.035, 0.012, 0.004, 0.003, 0.002, 0.001, 0.93, 0.004, 0.007];

const FEATURE_MAPS = FILTERS.map((filter) => {
  const output = Array.from({ length: 12 }, () => Array(12).fill(0) as number[]);
  let maximum = 0;
  for (let row = 0; row < 12; row += 1) {
    for (let column = 0; column < 12; column += 1) {
      let value = 0;
      for (let filterRow = 0; filterRow < 3; filterRow += 1) {
        for (let filterColumn = 0; filterColumn < 3; filterColumn += 1) {
          value += filter[filterRow][filterColumn] * DIGIT[row + filterRow][column + filterColumn];
        }
      }
      output[row][column] = Math.abs(value);
      maximum = Math.max(maximum, output[row][column]);
    }
  }
  return output.flat().map((value) => value / (maximum || 1));
});

export default function CnnExampleAnimation({ explanation }: { explanation: string }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const playRef = useRef<() => void>(() => undefined);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const timers: number[] = [];
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const find = <T extends Element>(selector: string) => root.querySelector<T>(selector);
    const findAll = <T extends Element>(selector: string) => [...root.querySelectorAll<T>(selector)];
    const later = (delay: number, action: () => void) => timers.push(window.setTimeout(action, delay));
    const clearPlayback = () => timers.splice(0).forEach(window.clearTimeout);

    const reset = () => {
      clearPlayback();
      findAll("[data-cnn-card]").forEach((element) => element.classList.remove("is-active", "is-done"));
      findAll("[data-cnn-wire]").forEach((element) => element.classList.remove("is-flowing"));
      findAll<HTMLElement>("[data-cnn-pixel]").forEach((element) => { element.style.opacity = "0.06"; });
      findAll<HTMLElement>("[data-feature-cell]").forEach((element) => { element.style.opacity = "0"; });
      findAll("[data-cnn-layer]").forEach((element) => element.classList.remove("is-lit"));
      findAll<HTMLElement>("[data-digit-bar]").forEach((element) => { element.style.height = "0"; });
      find("[data-cnn-scan]")?.classList.remove("is-visible");
      findAll("[data-cnn-result], [data-cnn-caveat], [data-cnn-explanation]").forEach((element) => element.classList.remove("is-visible"));
    };

    const moveScan = (row: number, column: number) => {
      const scan = find<HTMLElement>("[data-cnn-scan]");
      if (!scan) return;
      scan.style.left = `${3 + column * 8}px`;
      scan.style.top = `${3 + row * 8}px`;
    };

    const showFinalState = () => {
      reset();
      findAll("[data-cnn-card]").forEach((element) => element.classList.add("is-done"));
      findAll<HTMLElement>("[data-cnn-pixel]").forEach((element) => { element.style.opacity = element.dataset.value ?? "0.06"; });
      findAll<HTMLElement>("[data-feature-cell]").forEach((element) => { element.style.opacity = element.dataset.value ?? "0"; });
      findAll("[data-cnn-layer]").forEach((element) => element.classList.add("is-lit"));
      findAll<HTMLElement>("[data-digit-bar]").forEach((element) => { element.style.height = element.dataset.height ?? "3%"; });
      findAll("[data-cnn-result], [data-cnn-caveat], [data-cnn-explanation]").forEach((element) => element.classList.add("is-visible"));
    };

    const play = () => {
      if (reduceMotion) { showFinalState(); return; }
      reset();
      const cards = findAll<HTMLElement>("[data-cnn-card]");
      const visiblePixels = findAll<HTMLElement>("[data-cnn-pixel]").filter((pixel) => Number(pixel.dataset.value) > 0);
      let time = 300;
      later(time, () => cards[0]?.classList.add("is-active"));
      visiblePixels.forEach((pixel, index) => later(time + 250 + index * 24, () => { pixel.style.opacity = pixel.dataset.value ?? "1"; }));
      time += 250 + visiblePixels.length * 24 + 450;
      later(time, () => { cards[0]?.classList.replace("is-active", "is-done"); find("[data-wire-one]")?.classList.add("is-flowing"); });
      time += 900;
      later(time, () => {
        cards[1]?.classList.add("is-active");
        findAll("[data-cnn-layer]")[0]?.classList.add("is-lit");
        moveScan(0, 0);
        find("[data-cnn-scan]")?.classList.add("is-visible");
      });
      const scanPositions = Array.from({ length: 36 }, (_, index) => [Math.floor(index / 6) * 2, (index % 6) * 2]);
      scanPositions.forEach(([row, column], index) => later(time + 160 + index * 48, () => {
        moveScan(row, column);
        findAll<HTMLElement>("[data-feature-cell]").forEach((cell) => {
          const cellRow = Number(cell.dataset.row);
          const cellColumn = Number(cell.dataset.column);
          if (cellRow >= row && cellRow < row + 2 && cellColumn >= column && cellColumn < column + 2) {
            cell.style.opacity = cell.dataset.value ?? "0";
          }
        });
      }));
      time += 160 + scanPositions.length * 48 + 160;
      later(time, () => find("[data-cnn-scan]")?.classList.remove("is-visible"));
      findAll("[data-cnn-layer]").slice(1).forEach((layer, index) => later(time + 180 + index * 320, () => layer.classList.add("is-lit")));
      time += 1350;
      later(time, () => { cards[1]?.classList.replace("is-active", "is-done"); find("[data-wire-two]")?.classList.add("is-flowing"); });
      time += 900;
      later(time, () => {
        cards[2]?.classList.add("is-active");
        findAll<HTMLElement>("[data-digit-bar]").forEach((bar) => { bar.style.height = bar.dataset.height ?? "3%"; });
      });
      time += 1150;
      later(time, () => find("[data-cnn-result]")?.classList.add("is-visible"));
      time += 450;
      later(time, () => find("[data-cnn-caveat]")?.classList.add("is-visible"));
      time += 450;
      later(time, () => { cards[2]?.classList.replace("is-active", "is-done"); find("[data-cnn-explanation]")?.classList.add("is-visible"); });
    };

    playRef.current = play;
    let started = false;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !started) { started = true; play(); }
    }, { threshold: 0.3 });
    observer.observe(root);
    return () => { observer.disconnect(); clearPlayback(); playRef.current = () => undefined; };
  }, []);

  return <div className="sentiment-example-demo cnn-example-demo" ref={rootRef}>
    <h3>How a CNN recognizes a handwritten digit</h3>
    <div className="sentiment-animation-stage">
      <div className="sentiment-animation-card" data-cnn-card>
        <div className="sentiment-animation-step"><span>1</span><strong>What the model receives</strong></div>
        <p className="cnn-animation-subtitle">A handwritten digit made from pixel brightness values</p>
        <div className="cnn-pixel-wrap" role="img" aria-label="A pixel image of the handwritten digit 7">
          <div className="cnn-pixels" aria-hidden="true">
            {DIGIT.flatMap((row, rowIndex) => row.map((value, columnIndex) => <span key={`${rowIndex}-${columnIndex}`} data-cnn-pixel data-value={value} />))}
          </div>
          <span className="cnn-scan" data-cnn-scan aria-hidden="true" />
        </div>
        <p className="sentiment-animation-meta cnn-centered-meta">input · 14 × 14 grayscale pixels</p>
      </div>

      <div className="sentiment-animation-wire" data-cnn-wire data-wire-one aria-hidden="true"><span /></div>

      <div className="sentiment-animation-card" data-cnn-card>
        <div className="sentiment-animation-step"><span>⚙</span><strong>The CNN</strong></div>
        <p className="cnn-animation-subtitle">Small filters look for edges and strokes</p>
        <div className="cnn-feature-maps" aria-hidden="true">
          {FEATURE_MAPS.map((featureMap, mapIndex) => <div className="cnn-feature-map" key={mapIndex}>
            <div>{featureMap.map((value, cellIndex) => <span key={cellIndex} data-feature-cell data-row={Math.floor(cellIndex / 12)} data-column={cellIndex % 12} data-value={Math.max(0.08, value)} />)}</div>
            <small>{["horizontal", "vertical", "diagonal"][mapIndex]}</small>
          </div>)}
        </div>
        <div className="cnn-layer-flow" aria-label="Convolution, pooling, dense layer, then probabilities">
          {["Find strokes", "Shrink", "Combine", "Score"].map((label, index) => <span key={label}><b data-cnn-layer>{label}</b>{index < 3 && <i aria-hidden="true">→</i>}</span>)}
        </div>
      </div>

      <div className="sentiment-animation-wire" data-cnn-wire data-wire-two aria-hidden="true"><span /></div>

      <div className="sentiment-animation-card" data-cnn-card>
        <div className="sentiment-animation-step"><span>2</span><strong>What it predicts</strong></div>
        <p className="cnn-animation-subtitle">A score for each possible digit</p>
        <div className="cnn-score-chart" aria-label="Digit 7 has the highest score at 93 percent">
          {PROBABILITIES.map((probability, digit) => <div className={digit === 7 ? "is-winner" : ""} key={digit}>
            <span><i data-digit-bar data-height={`${Math.max(3, probability * 100)}%`} /></span>
            <small>{digit}</small>
          </div>)}
        </div>
        <div className="sentiment-result cnn-result" data-cnn-result><span>Predicted</span><strong>7</strong><em>93%</em></div>
        <p className="sentiment-caveat" data-cnn-caveat>A best guess—the CNN can still be fooled by messy handwriting.</p>
      </div>
    </div>
    <div className="sentiment-animation-explanation" data-cnn-explanation>
      <strong>What’s happening?</strong>
      <p>{explanation}</p>
    </div>
    <button className="sentiment-replay" type="button" onClick={() => playRef.current()} aria-label="Replay the handwritten digit prediction animation">↻ Replay</button>
  </div>;
}
