"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

// Plays a fixed sequence of steps once the figure scrolls into view. Each entry in
// `durations` is how long that step stays on screen before the next one starts.
// Reduced-motion viewers get the final step straight away.
export function useStepPlayer(durations: number[]) {
  const last = durations.length;
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const timers = useRef<number[]>([]);
  const durationsRef = useRef(durations);

  const clear = () => { timers.current.splice(0).forEach(window.clearTimeout); };

  const play = useCallback(() => {
    clear();
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setReducedMotion(true);
      setStep(last);
      return;
    }
    setStep(0);
    setPlaying(true);
    let elapsed = 0;
    durationsRef.current.forEach((duration, index) => {
      elapsed += duration;
      timers.current.push(window.setTimeout(() => {
        setStep(index + 1);
        if (index + 1 === last) setPlaying(false);
      }, elapsed));
    });
  }, [last]);

  useEffect(() => clear, []);
  return { step, last, playing, reducedMotion, play };
}

export default function LessonAnimation({ title, summary, caption, player, children }: {
  title: string;
  summary: string;
  caption: ReactNode;
  player: ReturnType<typeof useStepPlayer>;
  children: ReactNode;
}) {
  const ref = useRef<HTMLElement>(null);
  const started = useRef(false);
  const { play, playing, step, last } = player;

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !started.current) {
        started.current = true;
        play();
      }
    }, { threshold: 0.35 });
    observer.observe(element);
    return () => observer.disconnect();
  }, [play]);

  return <figure className="lesson-anim" ref={ref} aria-label={summary}>
    <header className="lesson-anim-header">
      <span className="lesson-anim-badge" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
      </span>
      <strong>{title}</strong>
      <span className="lesson-anim-progress" aria-hidden="true">
        {Array.from({ length: last + 1 }, (_, index) => <span key={index} className={index <= step ? "is-on" : ""} />)}
      </span>
      <button type="button" className="lesson-anim-replay" onClick={play} disabled={playing}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.3-5.6M4 4v4h4" /></svg>
        {playing ? "Playing" : "Replay"}
      </button>
    </header>
    <div className="lesson-anim-stage">{children}</div>
    <figcaption className="lesson-anim-caption" aria-live="polite">{caption}</figcaption>
  </figure>;
}
