from enum import Enum
from datetime import datetime
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    java_experience: Literal["beginner", "comfortable", "advanced"] = "comfortable"
    consent: Literal[True]
    consent_version: Literal["draft-research-consent-v1"]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("enter a valid email address")
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserRecord(BaseModel):
    user_id: str
    email: str
    name: str
    java_experience: str


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
    IMPLEMENT_CODE_OUTPUT_PREDICTION = "implement.code_output_prediction"
    IMPLEMENT_VARIABLE_PURPOSE = "implement.variable_purpose"
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


class TransitionRecord(TransitionCreate):
    created_at: str


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


class BehaviorEventCreate(BaseModel):
    event_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    event_type: Literal["content_exposure", "confidence_checkpoint", "navigation"]
    location: Location
    event_timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)


class BehaviorEventRecord(BehaviorEventCreate):
    learner_id: str
    sequence_index: int
    created_at: str
