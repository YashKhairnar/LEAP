from __future__ import annotations

import os
import secrets
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from threading import Lock
from time import monotonic
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .execution.cells import run_code_cell
from .assessments.service import AssessmentPhase, AssessmentSubmission, get_assessment, submit_assessment
from .assessments.bank import assessment_task
from .execution.sandbox import evaluate_code
from .tutoring.lesson_code import fixed_lesson_prerequisites
from .database import (
    IntegrityErrors,
    authenticate_user,
    create_user,
    initialize_database,
    list_progress,
    list_session_observations,
    resume_tutor_content,
    revoke_token,
    save_behavior_event,
    save_code_execution,
    save_generated_tutor_content,
    save_interaction,
    saved_stage_lesson,
    user_for_token,
)
from .execution.datasets import dataset_for_task
from .models import (
    AuthResponse,
    BehaviorEventCreate,
    BehaviorEventRecord,
    CodeEvaluationRequest,
    CodeEvaluationResult,
    CodeExecutionRequest,
    CodeExecutionResult,
    InteractionCreate,
    LoginRequest,
    PlannerRequest,
    PlannerResponse,
    ProgressRecord,
    PublicAuthResponse,
    RegisterRequest,
    TransitionRecord,
    TutorGenerationRequest,
    TutorGenerationResponse,
    TutorResumeResponse,
    GeneratedLessonContent,
    UserRecord,
)
from .tutoring.generator import TUTOR_PROMPT_VERSION, TutorGenerationUnavailable, generate_tutor_content
from .planning.client import WorldModelUnavailable, plan_next_action


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="LEAP API", version="0.1.0", lifespan=lifespan)

configured_origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auth_attempts: dict[str, deque[float]] = defaultdict(deque)
auth_attempts_lock = Lock()


@app.middleware("http")
async def limit_auth_attempts(request: Request, call_next):
    if request.url.path not in {"/api/auth/login", "/api/auth/register"}:
        return await call_next(request)
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    client = forwarded_for or (request.client.host if request.client else "unknown")
    now = monotonic()
    with auth_attempts_lock:
        attempts = auth_attempts[client]
        while attempts and attempts[0] < now - 60:
            attempts.popleft()
        if len(attempts) >= 10:
            return JSONResponse(status_code=429, content={"detail": "too many authentication attempts; try again shortly"})
        attempts.append(now)
    return await call_next(request)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def access_token(
    authorization: Annotated[Optional[str], Header()] = None,
    leap_session: Annotated[Optional[str], Cookie(alias="leap_session")] = None,
) -> str:
    if leap_session:
        return leap_session
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    return authorization.split(" ", 1)[1]


def current_user(token: Annotated[str, Depends(access_token)]) -> UserRecord:
    user = user_for_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid access token")
    return user


def set_session_cookie(response: Response, token: str) -> None:
    production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    response.set_cookie(
        "leap_session", token, httponly=True, secure=production,
        samesite="none" if production else "lax", max_age=60 * 60 * 24 * 30, path="/",
    )


@app.post("/api/auth/register", response_model=PublicAuthResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, response: Response) -> AuthResponse:
    try:
        result = create_user(
            str(uuid4()), request.password, request.java_experience, request.consent_version, request.analogy_preference
        )
        set_session_cookie(response, result.access_token)
        return result
    except IntegrityErrors as error:
        raise HTTPException(status_code=409, detail="unable to allocate a participant code") from error


@app.post("/api/auth/login", response_model=PublicAuthResponse)
def login(request: LoginRequest, response: Response) -> AuthResponse:
    result = authenticate_user(request.participant_code, request.password)
    if result is None:
        raise HTTPException(status_code=401, detail="invalid participant code or password")
    set_session_cookie(response, result.access_token)
    return result


@app.get("/api/auth/me", response_model=UserRecord)
def me(user: Annotated[UserRecord, Depends(current_user)]) -> UserRecord:
    return user


@app.get("/api/progress", response_model=list[ProgressRecord])
def progress(user: Annotated[UserRecord, Depends(current_user)]) -> list[ProgressRecord]:
    return list_progress(user.user_id)


@app.get("/api/assessments/{task}")
def task_assessment(task: str, user: Annotated[UserRecord, Depends(current_user)], phase: AssessmentPhase = "post"):
    try:
        return get_assessment(user.user_id, task, phase)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/assessments/{task}")
def task_assessment_submit(task: str, request: AssessmentSubmission, user: Annotated[UserRecord, Depends(current_user)], phase: AssessmentPhase = "post"):
    try:
        assessment_task(task)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    try:
        return submit_assessment(user.user_id, task, request, phase)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/code/evaluate", response_model=CodeEvaluationResult)
def code_evaluate(request: CodeEvaluationRequest, _: Annotated[UserRecord, Depends(current_user)]) -> CodeEvaluationResult:
    return evaluate_code(request.evaluator_id, request.code)


@app.get("/api/datasets/{task}")
def task_dataset(task: str, _: Annotated[UserRecord, Depends(current_user)]) -> dict:
    try:
        return dataset_for_task(task).public()
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/code/run", response_model=CodeExecutionResult)
def code_run(
    request: CodeExecutionRequest,
    user: Annotated[UserRecord, Depends(current_user)],
) -> CodeExecutionResult:
    try:
        # Lesson code is versioned and fixed, so canonical prerequisites are the
        # reproducible source of execution state across sessions and migrations.
        previous_cells = fixed_lesson_prerequisites(request.task, request.stage)
        result = run_code_cell(request, previous_cells)
        save_code_execution(request, result, user.user_id)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except IntegrityErrors as error:
        raise HTTPException(status_code=409, detail="execution already exists") from error


@app.post("/api/tutor/generate", response_model=TutorGenerationResponse)
def tutor_generate(
    request: TutorGenerationRequest,
    user: Annotated[UserRecord, Depends(current_user)],
) -> TutorGenerationResponse:
    try:
        persisted_lesson = saved_stage_lesson(user.user_id, request.task, request.stage, TUTOR_PROMPT_VERSION)
        persisted_lesson_model = (
            GeneratedLessonContent.model_validate(persisted_lesson)
            if persisted_lesson is not None else None
        )
        effective_request = request.model_copy(
            # Only reuse server-owned lessons for this learner. A browser cache can
            # belong to a different account or analogy preference.
            update={"existing_lesson": persisted_lesson_model,
                    "analogy_preference": user.analogy_preference,
                    "java_experience": user.java_experience}
        )
        generated = generate_tutor_content(effective_request, str(uuid4()))
        save_generated_tutor_content(effective_request, generated, user.user_id)
        return generated
    except TutorGenerationUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail=f"Tutor generation failed: {error}",
        ) from error


@app.get("/api/tutor/resume/{task}/{stage}/{step}", response_model=TutorResumeResponse)
def tutor_resume(
    task: str,
    stage: str,
    step: str,
    user: Annotated[UserRecord, Depends(current_user)],
    review: bool = False,
) -> TutorResumeResponse:
    return resume_tutor_content(user.user_id, task, stage, step, TUTOR_PROMPT_VERSION, review=review)


@app.post("/api/tutor/plan", response_model=PlannerResponse)
def tutor_plan(
    request: PlannerRequest,
    user: Annotated[UserRecord, Depends(current_user)],
) -> PlannerResponse:
    observations = list_session_observations(user.user_id, request.session_id)
    try:
        model_plan = plan_next_action(request, observations, user.user_id)
        return randomize_planner_action(model_plan)
    except WorldModelUnavailable:
        # Collection uses uniform exploration, not the shadow recommendation.
        # Keep delivering eligible actions when the optional shadow service fails.
        count = len(request.candidates)
        selected = secrets.randbelow(count)
        return PlannerResponse(
            planner_version="uniform_collection_fallback_v1", checkpoint="unavailable",
            selected_action_type=request.candidates[selected].action_type, selected_index=selected,
            current_state=[], predicted_state=[], candidate_predicted_states=[], candidate_distances=[],
            initialization="unavailable", initial_state_seed=0, goal_state=[], candidates=request.candidates,
            assignment_policy="uniform_random_v1", selection_probability=1 / count,
            action_probabilities=[1 / count] * count, shadow_status="unavailable",
        )


def randomize_planner_action(model_plan: PlannerResponse) -> PlannerResponse:
    """Deliver a uniform random action while retaining the model as a shadow policy."""
    action_count = len(model_plan.candidates)
    if action_count == 0 or len(model_plan.candidate_predicted_states) != action_count:
        raise ValueError("planner response does not contain one prediction per candidate")
    selected_index = secrets.randbelow(action_count)
    probability = 1.0 / action_count
    return model_plan.model_copy(update={
        "selected_action_type": model_plan.candidates[selected_index].action_type,
        "selected_index": selected_index,
        "predicted_state": model_plan.candidate_predicted_states[selected_index],
        "assignment_policy": "uniform_random_v1",
        "selection_probability": probability,
        "action_probabilities": [probability] * action_count,
        "world_model_selected_action_type": model_plan.selected_action_type,
        "world_model_selected_index": model_plan.selected_index,
    })


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, token: Annotated[str, Depends(access_token)]) -> None:
    revoke_token(token)
    response.delete_cookie("leap_session", path="/")


@app.post("/api/interactions", response_model=TransitionRecord, status_code=status.HTTP_201_CREATED)
def create_interaction(
    interaction: InteractionCreate,
    user: Annotated[UserRecord, Depends(current_user)],
) -> TransitionRecord:
    try:
        return save_interaction(interaction, user.user_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityErrors as error:
        raise HTTPException(status_code=409, detail="interaction already exists") from error


@app.post("/api/events", response_model=BehaviorEventRecord, status_code=status.HTTP_201_CREATED)
def create_event(
    event: BehaviorEventCreate,
    user: Annotated[UserRecord, Depends(current_user)],
) -> BehaviorEventRecord:
    try:
        return save_behavior_event(event, user.user_id)
    except IntegrityErrors as error:
        raise HTTPException(status_code=409, detail="event already exists") from error
