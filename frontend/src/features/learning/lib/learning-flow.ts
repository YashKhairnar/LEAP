export type StageScreen = "learn" | "practice";

export function initialStageScreen(step: string, practiceStarted: boolean): StageScreen {
  return step === "connect" && !practiceStarted ? "learn" : "practice";
}

export function nextPathAction(slug: string, baselineComplete: boolean, progress: { task_complete: boolean } | null): { label: string; href: string } {
  const root = `/learn/${slug}`;
  if (!baselineComplete) return { label: "Next: starting assessment", href: `${root}?view=starting-assessment` };
  if (progress?.task_complete) return { label: "Next: final assessment", href: `${root}?view=assessment` };
  if (progress) return { label: "Continue learning", href: `${root}/lesson` };
  return { label: "Next: explore the dataset", href: `${root}?view=dataset` };
}
