import type { InstructionalActionType } from "./instructional-actions";

export type Location = {
  task: string;
  stage: string;
  step: string;
};

export type ProgressionDecision = "remain_on_step" | "advance_step" | "advance_stage" | "complete_task";

export type Transition = {
  schema_version: "2.0";
  transition_id: string;
  learner_id: string;
  session_id: string;
  sequence_index: number;
  location_before: Location;
  instructional_action: {
    action_type: InstructionalActionType;
    content_id: string;
  };
  learner_action: {
    response: unknown;
  };
  observation: {
    correct: boolean;
    score: number;
    attempt: number;
    response_time_ms: number;
    misconception: string | null;
  };
  progression: {
    decision: ProgressionDecision;
  };
  location_after: Location;
};
