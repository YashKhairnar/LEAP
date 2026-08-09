export const INSTRUCTIONAL_ACTIONS = {
  activate: [
    "activate.java_concept_identification",
    "activate.java_output_prediction",
    "activate.java_code_explanation",
  ],
  connect: [
    "connect.concept_matching",
    "connect.comparison_selection",
    "connect.analogy_mapping",
  ],
  implement: [
    "implement.code_completion",
    "implement.code_output_prediction",
    "implement.variable_purpose",
  ],
  learn: [
    "learn.transfer_or_new",
    "learn.difference_explanation",
    "learn.concept_boundary",
  ],
  practice: [
    "practice.misconception_diagnosis",
    "practice.error_identification",
    "practice.pipeline_ordering",
  ],
  review: [
    "review.concept_summary",
    "review.novel_transfer",
    "review.confidence_checkpoint",
  ],
} as const;

export type InstructionalStep = keyof typeof INSTRUCTIONAL_ACTIONS;
export type InstructionalActionType = (typeof INSTRUCTIONAL_ACTIONS)[InstructionalStep][number];

export const ALL_INSTRUCTIONAL_ACTIONS: readonly InstructionalActionType[] = Object.values(INSTRUCTIONAL_ACTIONS).flat();

export function isActionAllowedForStep(step: InstructionalStep, action: InstructionalActionType): boolean {
  return (INSTRUCTIONAL_ACTIONS[step] as readonly InstructionalActionType[]).includes(action);
}
