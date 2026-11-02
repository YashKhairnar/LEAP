"use client";

import { useEffect, useRef } from "react";

const REVIEW = "The food was delicious. I would come back.";
const NETWORK_LAYERS: Array<[number, number[]]> = [
  [10, [14, 31, 48]],
  [42, [10, 24, 38, 52]],
  [74, [24, 38]],
];

const NETWORK_EDGES = NETWORK_LAYERS.slice(0, -1).flatMap(([x1, yValues], layerIndex) => {
  const [x2, nextYValues] = NETWORK_LAYERS[layerIndex + 1];
  return yValues.flatMap((y1) => nextYValues.map((y2) => ({ x1, y1, x2, y2 })));
});

export default function SentimentExampleAnimation({ explanation }: { explanation: string }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const playRef = useRef<() => void>(() => undefined);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const timers: number[] = [];
    const frames: number[] = [];
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const find = <T extends Element>(selector: string) => root.querySelector<T>(selector);
    const findAll = <T extends Element>(selector: string) => [...root.querySelectorAll<T>(selector)];
    const later = (delay: number, action: () => void) => {
      timers.push(window.setTimeout(action, delay));
    };
    const clearPlayback = () => {
      timers.splice(0).forEach(window.clearTimeout);
      frames.splice(0).forEach(window.cancelAnimationFrame);
    };
    const setReviewWithHighlights = () => {
      const typed = find<HTMLElement>("[data-typed-review]");
      if (typed) typed.innerHTML = 'The food was <span class="sentiment-highlight">delicious</span>. I would <span class="sentiment-highlight">come back</span>.';
    };
    const reset = () => {
      clearPlayback();
      findAll("[data-animation-card]").forEach((element) => element.classList.remove("is-active", "is-done"));
      findAll("[data-animation-wire]").forEach((element) => element.classList.remove("is-flowing"));
      findAll(".sentiment-highlight, [data-memory], .sentiment-network-node, .sentiment-network-edge").forEach((element) => element.classList.remove("is-lit"));
      findAll<HTMLElement>("[data-confidence-fill]").forEach((element) => { element.style.width = "0%"; });
      findAll("[data-result], [data-caveat], [data-explanation]").forEach((element) => element.classList.remove("is-visible"));
      const typed = find<HTMLElement>("[data-typed-review]");
      if (typed) typed.textContent = "";
      const caret = find<HTMLElement>("[data-review-caret]");
      if (caret) caret.hidden = false;
      for (const [selector, value] of [["[data-positive-percent]", "0%"], ["[data-neutral-percent]", "0%"], ["[data-negative-percent]", "0%"]] as const) {
        const percentage = find<HTMLElement>(selector);
        if (percentage) percentage.textContent = value;
      }
    };
    const countTo = (element: HTMLElement | null, target: number, duration: number) => {
      if (!element) return;
      const started = performance.now();
      const update = (time: number) => {
        const progress = Math.min(1, (time - started) / duration);
        element.textContent = `${Math.round(target * progress)}%`;
        if (progress < 1) frames.push(window.requestAnimationFrame(update));
      };
      frames.push(window.requestAnimationFrame(update));
    };
    const showFinalState = () => {
      reset();
      setReviewWithHighlights();
      const caret = find<HTMLElement>("[data-review-caret]");
      if (caret) caret.hidden = true;
      findAll("[data-animation-card]").forEach((element) => element.classList.add("is-done"));
      findAll(".sentiment-highlight, [data-memory]").forEach((element) => element.classList.add("is-lit"));
      findAll(".sentiment-network-node, .sentiment-network-edge").forEach((element, index) => {
        if (index % 2 === 0) element.classList.add("is-lit");
      });
      for (const [selector, value] of [["[data-positive-fill]", 92], ["[data-neutral-fill]", 6], ["[data-negative-fill]", 2]] as const) {
        const fill = find<HTMLElement>(selector);
        if (fill) fill.style.width = `${value}%`;
      }
      for (const [selector, value] of [["[data-positive-percent]", "92%"], ["[data-neutral-percent]", "6%"], ["[data-negative-percent]", "2%"]] as const) {
        const percentage = find<HTMLElement>(selector);
        if (percentage) percentage.textContent = value;
      }
      findAll("[data-result], [data-caveat], [data-explanation]").forEach((element) => element.classList.add("is-visible"));
    };
    const play = () => {
      if (reduceMotion) { showFinalState(); return; }
      reset();
      const cards = findAll<HTMLElement>("[data-animation-card]");
      const typed = find<HTMLElement>("[data-typed-review]");
      let time = 300;
      later(time, () => cards[0]?.classList.add("is-active"));
      for (let index = 1; index <= REVIEW.length; index += 1) {
        time += 34;
        later(time, () => { if (typed) typed.textContent = REVIEW.slice(0, index); });
      }
      time += 220;
      later(time, () => {
        const caret = find<HTMLElement>("[data-review-caret]");
        if (caret) caret.hidden = true;
        setReviewWithHighlights();
        findAll(".sentiment-highlight").forEach((element, index) => later(index * 300, () => element.classList.add("is-lit")));
      });
      time += 900;
      later(time, () => { cards[0]?.classList.replace("is-active", "is-done"); find("[data-wire-one]")?.classList.add("is-flowing"); });
      time += 850;
      later(time, () => cards[1]?.classList.add("is-active"));
      const network = findAll(".sentiment-network-node, .sentiment-network-edge");
      for (let pulse = 0; pulse < 8; pulse += 1) {
        later(time + pulse * 120, () => network.forEach((element, index) => element.classList.toggle("is-lit", (index + pulse) % 3 !== 0)));
      }
      findAll("[data-memory]").forEach((element, index) => later(time + 260 + index * 330, () => element.classList.add("is-lit")));
      time += 1450;
      later(time, () => { cards[1]?.classList.replace("is-active", "is-done"); find("[data-wire-two]")?.classList.add("is-flowing"); });
      time += 850;
      later(time, () => {
        cards[2]?.classList.add("is-active");
        const positive = find<HTMLElement>("[data-positive-fill]");
        const neutral = find<HTMLElement>("[data-neutral-fill]");
        const negative = find<HTMLElement>("[data-negative-fill]");
        if (positive) positive.style.width = "92%";
        if (neutral) neutral.style.width = "6%";
        if (negative) negative.style.width = "2%";
        countTo(find("[data-positive-percent]"), 92, 1000);
        countTo(find("[data-neutral-percent]"), 6, 1000);
        countTo(find("[data-negative-percent]"), 2, 1000);
      });
      time += 1150;
      later(time, () => find("[data-result]")?.classList.add("is-visible"));
      time += 500;
      later(time, () => find("[data-caveat]")?.classList.add("is-visible"));
      time += 500;
      later(time, () => { cards[2]?.classList.replace("is-active", "is-done"); find("[data-explanation]")?.classList.add("is-visible"); });
    };

    playRef.current = play;
    let started = false;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !started) { started = true; play(); }
    }, { threshold: 0.3 });
    observer.observe(root);
    return () => { observer.disconnect(); clearPlayback(); playRef.current = () => undefined; };
  }, []);

  return <div className="sentiment-example-demo" ref={rootRef}>
    <h3>How a model sorts a new review</h3>
    <div className="sentiment-animation-stage">
      <div className="sentiment-animation-card" data-animation-card>
        <div className="sentiment-animation-step"><span>1</span><strong>What the model receives</strong></div>
        <div className="sentiment-review-sample">
          <div className="sentiment-stars" aria-label="Five-star review">★★★★★</div>
          <span data-typed-review /> <span className="sentiment-caret" data-review-caret aria-hidden="true" />
        </div>
        <p className="sentiment-animation-meta">input · new review</p>
      </div>

      <div className="sentiment-animation-wire" data-animation-wire data-wire-one aria-hidden="true"><span /></div>

      <div className="sentiment-animation-card" data-animation-card>
        <div className="sentiment-animation-step"><span>⚙</span><strong>The model</strong></div>
        <svg className="sentiment-network" viewBox="0 0 84 62" aria-hidden="true">
          {NETWORK_EDGES.map((edge, index) => <line className="sentiment-network-edge" key={`edge-${index}`} {...edge} />)}
          {NETWORK_LAYERS.flatMap(([x, yValues]) => yValues.map((y) => <circle className="sentiment-network-node" key={`${x}-${y}`} cx={x} cy={y} r="5" />))}
        </svg>
        <p className="sentiment-memory-title">Patterns learned from earlier reviews</p>
        <div className="sentiment-memory-list">
          <div data-memory><span>“Delicious pasta!”</span><em className="is-positive">positive</em></div>
          <div data-memory><span>“Food was cold.”</span><em className="is-negative">negative</em></div>
          <div data-memory><span>“Will come back soon.”</span><em className="is-positive">positive</em></div>
        </div>
      </div>

      <div className="sentiment-animation-wire" data-animation-wire data-wire-two aria-hidden="true"><span /></div>

      <div className="sentiment-animation-card" data-animation-card>
        <div className="sentiment-animation-step"><span>2</span><strong>What it predicts</strong></div>
        <div className="sentiment-confidence-bars">
          <ConfidenceBar label="Positive" value={92} tone="positive" />
          <ConfidenceBar label="Neutral" value={6} tone="neutral" />
          <ConfidenceBar label="Negative" value={2} tone="negative" />
        </div>
        <div className="sentiment-result" data-result><span>Predicted</span><strong>positive</strong></div>
        <p className="sentiment-caveat" data-caveat>A best guess, not a certainty. It can still be wrong.</p>
      </div>
    </div>
    <div className="sentiment-animation-explanation" data-explanation>
      <strong>What’s happening?</strong>
      <p>{explanation}</p>
    </div>
    <button className="sentiment-replay" type="button" onClick={() => playRef.current()} aria-label="Replay the sentiment prediction animation">↻ Replay</button>
  </div>;
}

function ConfidenceBar({ label, value, tone }: { label: string; value: number; tone: "positive" | "neutral" | "negative" }) {
  return <div className="sentiment-confidence-row">
    <span>{label}</span>
    <div className="sentiment-confidence-track" role="progressbar" aria-label={`${label} confidence`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}>
      <span className={`sentiment-confidence-fill is-${tone}`} data-confidence-fill data-positive-fill={tone === "positive" || undefined} data-neutral-fill={tone === "neutral" || undefined} data-negative-fill={tone === "negative" || undefined} />
    </div>
    <span className="sentiment-confidence-percent" data-positive-percent={tone === "positive" || undefined} data-neutral-percent={tone === "neutral" || undefined} data-negative-percent={tone === "negative" || undefined}>0%</span>
  </div>;
}
