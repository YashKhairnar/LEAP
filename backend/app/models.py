import ast
from datetime import datetime
from enum import Enum
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

AnalogyPreference = Literal["pure_ml", "everyday", "java"]


class RegisterRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    # Retained in storage/API records for compatibility with existing accounts.
    # New signup forms do not ask learners to self-rate their Java experience.
    java_experience: Literal["unspecified", "none", "beginner", "comfortable", "advanced"] = "unspecified"
    analogy_preference: AnalogyPreference = "java"
    consent: Literal[True]
    consent_version: Literal["draft-research-consent-v1"]


class LoginRequest(BaseModel):
    participant_code: str = Field(min_length=15, max_length=15, pattern=r"^LP-[A-F0-9]{12}$")
    password: str = Field(min_length=1, max_length=128)

    @field_validator("participant_code", mode="before")
    @classmethod
    def normalize_participant_code(cls, value: str) -> str:
        return value.strip().upper()


class UserRecord(BaseModel):
    user_id: str
    participant_code: str
    java_experience: str
    analogy_preference: AnalogyPreference = "java"


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserRecord


class PublicAuthResponse(BaseModel):
    user: UserRecord


class Location(BaseModel):
    task: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    step: str = Field(min_length=1)


class InstructionalActionType(str, Enum):
    ACTIVATE_JAVA_CONCEPT_IDENTIFICATION = "activate.java_concept_identification"
    ACTIVATE_JAVA_OUTPUT_PREDICTION = "activate.java_output_prediction"
    ACTIVATE_JAVA_CODE_EXPLANATION = "activate.java_code_explanation"
    CONNECT_CONCEPT_MATCHING = "connect.concept_matching"
    CONNECT_COMPARISON_SELECTION = "connect.comparison_selection"
    CONNECT_ANALOGY_MAPPING = "connect.analogy_mapping"
    IMPLEMENT_CODE_COMPLETION = "implement.code_completion"
    IMPLEMENT_CODE_DEBUGGING = "implement.code_debugging"
    IMPLEMENT_CODE_CONSTRUCTION = "implement.code_construction"
    LEARN_TRANSFER_OR_NEW = "learn.transfer_or_new"
    LEARN_DIFFERENCE_EXPLANATION = "learn.difference_explanation"
    LEARN_CONCEPT_BOUNDARY = "learn.concept_boundary"
    PRACTICE_MISCONCEPTION_DIAGNOSIS = "practice.misconception_diagnosis"
    PRACTICE_ERROR_IDENTIFICATION = "practice.error_identification"
    PRACTICE_PIPELINE_ORDERING = "practice.pipeline_ordering"
    REVIEW_CONCEPT_SUMMARY = "review.concept_summary"
    REVIEW_NOVEL_TRANSFER = "review.novel_transfer"
    REVIEW_CONFIDENCE_CHECKPOINT = "review.confidence_checkpoint"


class InstructionalAction(BaseModel):
    action_type: InstructionalActionType
    content_id: str = Field(min_length=1)


class ContentCreate(BaseModel):
    content_id: str = Field(min_length=1)
    task: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    step: str = Field(min_length=1)
    action_type: InstructionalActionType
    prompt: str = Field(min_length=1)
    options: Optional[List[str]] = None
    correct_answer: Any
    explanation: str = Field(min_length=1)
    misconception: Optional[str] = None
    learning_objectives: List[str] = Field(default_factory=list)
    lesson_content: Optional[dict[str, Any]] = None
    planner_decision: Optional[dict[str, Any]] = None
    generation_metadata: Optional[dict[str, Any]] = None


class ContentRecord(ContentCreate):
    created_at: str


class LearnerAction(BaseModel):
    response: Any


class Observation(BaseModel):
    correct: bool
    score: float = Field(ge=0.0, le=1.0)
    attempt: int = Field(ge=1)
    response_time_ms: int = Field(ge=0)
    misconception: Optional[str] = None
    # None means a legacy client did not measure this; never infer independence.
    hint_used: Optional[bool] = None
    answer_revealed_before_attempt: Optional[bool] = None
    evidence_kind: Optional[Literal["independent", "hint_assisted", "post_feedback_retry", "unknown"]] = None
    timing_version: Optional[str] = None
    exposure_id: Optional[str] = None


class Progression(BaseModel):
    decision: Literal[
        "remain_on_step",
        "advance_step",
        "advance_stage",
        "complete_task",
    ]


class TransitionCreate(BaseModel):
    schema_version: Literal["2.1"] = "2.1"
    transition_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    sequence_index: int = Field(ge=0)
    location_before: Location
    instructional_action: InstructionalAction
    learner_action: LearnerAction
    observation: Observation
    progression: Progression
    location_after: Location
    event_timestamp: datetime
    selection_policy: str = Field(default="predefined_sequence_v1", min_length=1)
    presentation_id: Optional[str] = Field(default=None, min_length=1)


class TransitionRecord(TransitionCreate):
    created_at: str
    learner_state: Optional[dict[str, Any]] = None
    collection_mode: str = "legacy_unknown"


class InteractionCreate(BaseModel):
    session_id: str = Field(min_length=1)
    content: ContentCreate
    transition_id: str = Field(min_length=1)
    location_before: Location
    instructional_action: InstructionalAction
    learner_action: LearnerAction
    observation: Observation
    progression: Progression
    location_after: Location
    event_timestamp: datetime
    selection_policy: str = Field(default="predefined_sequence_v1", min_length=1)
    presentation_id: Optional[str] = Field(default=None, min_length=1)
    learner_state: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_contract(self):
        if self.instructional_action.content_id != self.content.content_id:
            raise ValueError("instructional action and content IDs must match")
        if self.instructional_action.action_type != self.content.action_type:
            raise ValueError("instructional action and content action types must match")
        before = self.location_before
        if (self.content.task, self.content.stage, self.content.step) != (
            before.task, before.stage, before.step
        ):
            raise ValueError("content location must match location_before")
        action_step = self.instructional_action.action_type.value.split(".", 1)[0]
        if action_step != before.step:
            raise ValueError("instructional action phase must match location_before.step")
        if self.location_after.task != before.task:
            raise ValueError("location_after.task must match location_before.task")
        return self


class BehaviorEventCreate(BaseModel):
    event_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    event_type: Literal["content_presented", "content_exposure", "confidence_checkpoint", "navigation"]
    location: Location
    event_timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)


class BehaviorEventRecord(BehaviorEventCreate):
    learner_id: str
    sequence_index: int
    created_at: str
    collection_mode: str = "legacy_unknown"


class ProgressRecord(BaseModel):
    task: str
    completed_stages: int = Field(ge=0)
    total_stages: int = Field(ge=1)
    task_complete: bool
    current_stage: Optional[str] = None
    current_step: Optional[str] = None
    updated_at: str


class CodeEvaluationRequest(BaseModel):
    evaluator_id: Literal[
        "data_loading", "train_test_split", "tfidf_vectorization",
        "model_training", "prediction", "evaluation",
        "cnn_load_images", "cnn_normalize", "cnn_build", "cnn_train",
        "cnn_predict", "cnn_evaluate", "reg_load_data", "reg_split",
        "reg_scale", "reg_train", "reg_predict", "reg_evaluate",
    ]
    code: str = Field(min_length=1, max_length=4000)


class CodeEvaluationResult(BaseModel):
    correct: bool
    feedback: str


class CodeExecutionRequest(BaseModel):
    execution_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    task: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    step: str = Field(min_length=1)
    code: str = Field(min_length=1, max_length=8000)


class CodeExecutionResult(BaseModel):
    execution_id: str
    success: bool
    stdout: str
    stderr: str
    result: Any = None
    table_preview: Optional[dict[str, Any]] = None
    plots: List[str] = Field(default_factory=list, max_length=3)
    duration_ms: int = Field(ge=0)
    dataset: dict[str, Any]
    replayed_cells: int = Field(ge=0)
    runtime: dict[str, str]


class TutorContent(BaseModel):
    question: str = Field(min_length=1)
    options: List[str] = Field(min_length=2, max_length=5)
    expected_answer: str = Field(min_length=1)
    hint: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    concepts_tested: List[str]

    @model_validator(mode="after")
    def validate_expected_option(self):
        if self.expected_answer not in self.options:
            raise ValueError("expected_answer must exactly match one option")
        return self


class GeneratedLessonSection(BaseModel):
    type: Literal[
        "meaning", "concept", "analogy", "example", "code", "result", "why_it_matters",
        # Keep accepting lessons saved before the six-part curriculum was introduced.
        "concept_bridge", "real_life_analogy", "data_preview", "pipeline",
        "transformation", "warning", "metric",
    ]
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    items: List[str] = Field(default_factory=list, max_length=6)
    code: Optional[str] = None
    language: Optional[str] = None


class CodeExperiment(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    find: str = Field(min_length=1, max_length=6000)
    replace: str = Field(min_length=1, max_length=6000)
    expected_change: str = Field(min_length=1, max_length=600)


class GeneratedLessonContent(BaseModel):
    title: str = Field(min_length=1)
    introduction: str = Field(min_length=1)
    sections: List[GeneratedLessonSection] = Field(min_length=3, max_length=6)
    code_explanation: List[str] = Field(default_factory=list, max_length=6)
    # Strings remain readable for historical completed lessons.
    try_this: List[Union[CodeExperiment, str]] = Field(default_factory=list, max_length=2)
    key_takeaway: str = Field(default="", max_length=160)

    @model_validator(mode="after")
    def validate_sections(self):
        six_part_order = ["meaning", "analogy", "example", "code", "result", "why_it_matters"]
        pure_ml_order = ["meaning", "concept", "example", "code", "result", "why_it_matters"]
        section_types = [section.type for section in self.sections]
        new_only_types = set(six_part_order) - {"code"}
        if any(section_type in new_only_types or section_type == "concept" for section_type in section_types):
            if section_types not in (six_part_order, pure_ml_order):
                raise ValueError("new lessons must use the complete teaching sequence in order")
        # Legacy validation lets learners continue reviewing lessons saved under
        # an earlier prompt version without weakening the new generation schema.
        if not any(section.type == "code" for section in self.sections):
            raise ValueError("lesson must include a code section")
        if not any(section.type in ("analogy", "real_life_analogy", "concept") for section in self.sections):
            raise ValueError("lesson must include an analogy or direct-concept section")
        for section in self.sections:
            if section.type == "code" and (not section.code or not section.language):
                raise ValueError("code sections require code and language")
        lesson_code = next(section.code for section in self.sections if section.type == "code")
        for experiment in self.try_this:
            if isinstance(experiment, str):
                continue
            if lesson_code.count(experiment.find) != 1:
                raise ValueError("experiment must match exactly one location in the lesson code")
            if experiment.find == experiment.replace:
                raise ValueError("experiment must change the lesson code")
            try:
                ast.parse(lesson_code.replace(experiment.find, experiment.replace, 1))
            except SyntaxError as error:
                raise ValueError("experiment must produce valid Python") from error
        return self


class TutorGenerationRequest(BaseModel):
    task: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    step: str = Field(min_length=1)
    action_type: InstructionalActionType
    reference_prompt: str = Field(min_length=1, max_length=2000)
    learning_objectives: List[str] = Field(default_factory=list, max_length=20)
    existing_lesson: Optional[GeneratedLessonContent] = None
    planner_decision: Optional[dict[str, Any]] = None
    # The HTTP handler replaces these with the authenticated account's settings.
    analogy_preference: AnalogyPreference = "java"
    java_experience: str = "unspecified"

    @model_validator(mode="after")
    def validate_action_phase(self):
        if self.action_type.value.split(".", 1)[0] != self.step:
            raise ValueError("action phase must match step")
        return self


class TutorGenerationResponse(BaseModel):
    content_instance_id: str = Field(min_length=1)
    model: str
    prompt_version: str = Field(min_length=1)
    code_version: str = Field(min_length=1)
    dataset: dict[str, Any]
    lesson: GeneratedLessonContent
    content: TutorContent
    collection_content: Optional[ContentCreate] = None


class TutorQuestionState(BaseModel):
    presentation_id: Optional[str] = None
    answer: Optional[str] = None
    correct: Optional[bool] = None
    attempt: int = Field(default=1, ge=1)
    hint_used: bool = False


class TutorResumeResponse(BaseModel):
    task: str
    stage: str
    step: str
    lesson: Optional[GeneratedLessonContent] = None
    active_question: Optional[TutorGenerationResponse] = None
    action_type: Optional[InstructionalActionType] = None
    question_state: Optional[TutorQuestionState] = None


class PlannerCandidate(BaseModel):
    action_type: InstructionalActionType
    prompt: str = Field(min_length=1, max_length=4000)


class PlannerRequest(BaseModel):
    session_id: str = Field(min_length=1)
    task: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    step: str = Field(min_length=1)
    candidates: List[PlannerCandidate] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_candidate_phases(self):
        if len({candidate.action_type for candidate in self.candidates}) != len(self.candidates):
            raise ValueError("candidate actions must be distinct")
        if any(candidate.action_type.value.split(".", 1)[0] != self.step for candidate in self.candidates):
            raise ValueError("all candidate action phases must match step")
        return self


class PlannerResponse(BaseModel):
    planner_version: str
    checkpoint: str
    selected_action_type: InstructionalActionType
    selected_index: int
    current_state: List[float]
    predicted_state: List[float]
    candidate_predicted_states: List[List[float]]
    candidate_distances: List[float]
    initialization: Literal["deterministic_random_initial_state", "encoded_session_history", "unavailable"]
    shadow_status: Literal["available", "unavailable"] = "available"
    initial_state_seed: int
    goal_state: List[float]
    candidates: List[PlannerCandidate]
    assignment_policy: Optional[Literal["uniform_random_v1"]] = None
    selection_probability: Optional[float] = Field(default=None, gt=0.0, le=1.0)
    action_probabilities: List[float] = Field(default_factory=list)
    world_model_selected_action_type: Optional[InstructionalActionType] = None
    world_model_selected_index: Optional[int] = Field(default=None, ge=0)
