from __future__ import annotations

from contextlib import asynccontextmanager
from collections import defaultdict, deque
import os
from threading import Lock
from time import monotonic
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import (
    IntegrityErrors,
    authenticate_user,
    create_user,
    initialize_database,
    list_progress,
    save_behavior_event,
    save_interaction,
    user_for_token,
    revoke_token,
)
from .models import (
    AuthResponse,
    BehaviorEventCreate,
    BehaviorEventRecord,
    InteractionCreate,
    LoginRequest,
    PublicAuthResponse,
    ProgressRecord,
    RegisterRequest,
    TransitionRecord,
    UserRecord,
    CodeEvaluationRequest,
    CodeEvaluationResult,
)
from .code_sandbox import evaluate_code


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
        result = create_user(str(uuid4()), request.email, request.password, request.name, request.java_experience, request.consent_version)
        set_session_cookie(response, result.access_token)
        return result
    except IntegrityErrors as error:
        raise HTTPException(status_code=409, detail="an account with this email already exists") from error


@app.post("/api/auth/login", response_model=PublicAuthResponse)
def login(request: LoginRequest, response: Response) -> AuthResponse:
    result = authenticate_user(request.email, request.password)
    if result is None:
        raise HTTPException(status_code=401, detail="invalid email or password")
    set_session_cookie(response, result.access_token)
    return result


@app.get("/api/auth/me", response_model=UserRecord)
def me(user: Annotated[UserRecord, Depends(current_user)]) -> UserRecord:
    return user


@app.get("/api/progress", response_model=list[ProgressRecord])
def progress(user: Annotated[UserRecord, Depends(current_user)]) -> list[ProgressRecord]:
    return list_progress(user.user_id)


@app.post("/api/code/evaluate", response_model=CodeEvaluationResult)
def code_evaluate(request: CodeEvaluationRequest, _: Annotated[UserRecord, Depends(current_user)]) -> CodeEvaluationResult:
    return evaluate_code(request.evaluator_id, request.code)


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
