"use client";

import { useEffect, useRef } from "react";

const PRICE = 485_000;
const MIN_PRICE = 300_000;
const MAX_PRICE = 700_000;
const NETWORK_LAYERS: Array<[number, number[]]> = [
  [10, [14, 31, 48]],
  [42, [10, 24, 38, 52]],
  [74, [31]],
];

const NETWORK_EDGES = NETWORK_LAYERS.slice(0, -1).flatMap(([x1, yValues], layerIndex) => {
  const [x2, nextYValues] = NETWORK_LAYERS[layerIndex + 1];
  return yValues.flatMap((y1) => nextYValues.map((y2) => ({ x1, y1, x2, y2 })));
});

export default function RegressionExampleAnimation({ explanation }: { explanation: string }) {
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
    const later = (delay: number, action: () => void) => { timers.push(window.setTimeout(action, delay)); };
    const clearPlayback = () => {
      timers.splice(0).forEach(window.clearTimeout);
      frames.splice(0).forEach(window.cancelAnimationFrame);
    };
    const setPrice = (value: number) => {
      const price = find<HTMLElement>("[data-estimated-price]");
      if (price) price.textContent = `$${value.toLocaleString("en-US")}`;
    };
    const reset = () => {
      clearPlayback();
      findAll("[data-animation-card]").forEach((element) => element.classList.remove("is-active", "is-done"));
      findAll("[data-animation-wire]").forEach((element) => element.classList.remove("is-flowing"));
      findAll("[data-house-feature], [data-memory], .sentiment-network-node, .sentiment-network-edge").forEach((element) => element.classList.remove("is-lit"));
      findAll("[data-actual-price], [data-explanation]").forEach((element) => element.classList.remove("is-visible"));
      setPrice(0);
      const pin = find<HTMLElement>("[data-price-pin]");
      if (pin) { pin.style.left = "0%"; pin.style.opacity = "0"; }
    };
    const countPrice = (duration: number) => {
      const started = performance.now();
      const update = (time: number) => {
        const progress = Math.min(1, (time - started) / duration);
        const eased = 1 - Math.pow(1 - progress, 3);
        setPrice(Math.round((PRICE * eased) / 1000) * 1000);
        if (progress < 1) frames.push(window.requestAnimationFrame(update));
      };
      frames.push(window.requestAnimationFrame(update));
    };
    const showFinalState = () => {
      reset();
      findAll("[data-animation-card]").forEach((element) => element.classList.add("is-done"));
      findAll("[data-house-feature], [data-memory]").forEach((element) => element.classList.add("is-lit"));
      findAll(".sentiment-network-node, .sentiment-network-edge").forEach((element, index) => {
        if (index % 2 === 0) element.classList.add("is-lit");
      });
      setPrice(PRICE);
      const pin = find<HTMLElement>("[data-price-pin]");
      if (pin) { pin.style.left = `${((PRICE - MIN_PRICE) / (MAX_PRICE - MIN_PRICE)) * 100}%`; pin.style.opacity = "1"; }
      findAll("[data-actual-price], [data-explanation]").forEach((element) => element.classList.add("is-visible"));
    };
    const play = () => {
      if (reduceMotion) { showFinalState(); return; }
      reset();
      const cards = findAll<HTMLElement>("[data-animation-card]");
      let time = 300;
      later(time, () => cards[0]?.classList.add("is-active"));
      findAll("[data-house-feature]").forEach((element, index) => later(time + 260 + index * 240, () => element.classList.add("is-lit")));
      time += 1550;
      later(time, () => { cards[0]?.classList.replace("is-active", "is-done"); find("[data-wire-one]")?.classList.add("is-flowing"); });
      time += 850;
      later(time, () => cards[1]?.classList.add("is-active"));
      const network = findAll(".sentiment-network-node, .sentiment-network-edge");
      for (let pulse = 0; pulse < 8; pulse += 1) {
        later(time + pulse * 120, () => network.forEach((element, index) => element.classList.toggle("is-lit", (index + pulse) % 3 !== 0)));
      }
      findAll("[data-memory]").forEach((element, index) => later(time + 260 + index * 330, () => element.classList.add("is-lit")));
      time += 1550;
      later(time, () => { cards[1]?.classList.replace("is-active", "is-done"); find("[data-wire-two]")?.classList.add("is-flowing"); });
      time += 850;
      later(time, () => {
        cards[2]?.classList.add("is-active");
        countPrice(1200);
        const pin = find<HTMLElement>("[data-price-pin]");
        if (pin) {
          pin.style.opacity = "1";
          frames.push(window.requestAnimationFrame(() => { pin.style.left = `${((PRICE - MIN_PRICE) / (MAX_PRICE - MIN_PRICE)) * 100}%`; }));
        }
      });
      time += 1450;
      later(time, () => find("[data-actual-price]")?.classList.add("is-visible"));
      time += 650;
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

  return <div className="sentiment-example-demo regression-example-demo" ref={rootRef}>
    <h3>How a model estimates a house price</h3>
    <div className="sentiment-animation-stage">
      <div className="sentiment-animation-card" data-animation-card>
        <div className="sentiment-animation-step"><span>1</span><strong>What the model receives</strong></div>
        <div className="regression-house-icon" aria-hidden="true"><svg viewBox="0 0 44 36"><path d="M4 17 22 3l18 14M9 13v20h26V13M18 33v-10h8v10" /></svg></div>
        <div className="regression-features">
          <div data-house-feature><strong>3</strong><span>bedrooms</span></div>
          <div data-house-feature><strong>2</strong><span>bathrooms</span></div>
          <div data-house-feature><strong>1,800</strong><span>square feet</span></div>
          <div data-house-feature><strong>20</strong><span>years old</span></div>
        </div>
        <p className="sentiment-animation-meta">inputs · house details</p>
      </div>

      <div className="sentiment-animation-wire" data-animation-wire data-wire-one aria-hidden="true"><span /></div>

      <div className="sentiment-animation-card" data-animation-card>
        <div className="sentiment-animation-step"><span>⚙</span><strong>The model</strong></div>
        <svg className="sentiment-network" viewBox="0 0 84 62" aria-hidden="true">
          {NETWORK_EDGES.map((edge, index) => <line className="sentiment-network-edge" key={`edge-${index}`} {...edge} />)}
          {NETWORK_LAYERS.flatMap(([x, yValues]) => yValues.map((y) => <circle className="sentiment-network-node" key={`${x}-${y}`} cx={x} cy={y} r="5" />))}
        </svg>
        <p className="sentiment-memory-title">Patterns learned from earlier sales</p>
        <div className="sentiment-memory-list">
          <div data-memory><span>2 bd · 1,100 ft²</span><em className="is-price">$395k</em></div>
          <div data-memory><span>4 bd · 2,400 ft²</span><em className="is-price">$610k</em></div>
          <div data-memory><span>3 bd · 1,700 ft²</span><em className="is-price">$472k</em></div>
        </div>
      </div>

      <div className="sentiment-animation-wire" data-animation-wire data-wire-two aria-hidden="true"><span /></div>

      <div className="sentiment-animation-card" data-animation-card>
        <div className="sentiment-animation-step"><span>2</span><strong>What it predicts</strong></div>
        <p className="regression-price-label">Estimated sale price</p>
        <p className="regression-estimated-price" data-estimated-price>$0</p>
        <div className="regression-price-scale" aria-hidden="true">
          <span className="regression-price-axis" />
          <span className="regression-price-min">$300k</span>
          <span className="regression-price-max">$700k</span>
          <span className="regression-price-pin" data-price-pin />
        </div>
        <div className="regression-actual-price" data-actual-price><span>Actual sale price</span><strong>compare later →</strong></div>
      </div>
    </div>
    <div className="sentiment-animation-explanation" data-explanation>
      <strong>What’s happening?</strong>
      <p>{explanation}</p>
    </div>
    <button className="sentiment-replay" type="button" onClick={() => playRef.current()} aria-label="Replay the house-price prediction animation">↻ Replay</button>
  </div>;
}
