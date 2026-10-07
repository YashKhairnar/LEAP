import type { CSSProperties } from "react";

export default function CircularProgress({ value, label = "Task progress" }: { value: number; label?: string }) {
  const progress = Math.min(100, Math.max(0, Math.round(value)));
  const style = { "--progress": `${progress * 3.6}deg` } as CSSProperties;

  return <div className="lesson-progress-summary">
    <div
      className="lesson-progress-ring"
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={progress}
      style={style}
    >
      <strong>{progress}%</strong>
    </div>
    <span>{label}</span>
  </div>;
}
