/** Visible, foreground time only. Monotonic timestamps are supplied by the UI. */
export class QuestionExposureClock {
  private started: number | null = null;
  private accumulated = 0;
  reset() { this.started = null; this.accumulated = 0; }
  setVisible(visible: boolean, now: number) {
    if (visible && this.started === null) this.started = now;
    if (!visible && this.started !== null) {
      this.accumulated += Math.max(0, now - this.started);
      this.started = null;
    }
  }
  elapsed(now: number) { return Math.round(this.accumulated + (this.started === null ? 0 : Math.max(0, now - this.started))); }
}

export type AttemptEvidence = {
  hint_used: boolean;
  answer_revealed_before_attempt: boolean;
  evidence_kind: "independent" | "hint_assisted" | "post_feedback_retry" | "unknown";
  timing_version: "visible_foreground_v1";
  exposure_id: string;
};

export function evidenceKind(hint: boolean, revealed: boolean, known: boolean): AttemptEvidence["evidence_kind"] {
  return revealed ? "post_feedback_retry" : hint ? "hint_assisted" : known ? "independent" : "unknown";
}
