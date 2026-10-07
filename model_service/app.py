from __future__ import annotations

import hmac
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from leap.planning.runtime import WorldModelRuntime
from pydantic import BaseModel, Field


class Candidate(BaseModel):
    action_type: str = Field(min_length=1)
    prompt: str = Field(min_length=1, max_length=4000)


class PlanRequest(BaseModel):
    task: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    step: str = Field(min_length=1)
    candidates: list[Candidate] = Field(min_length=1, max_length=3)
    observations: list[dict[str, Any]] = Field(default_factory=list)
    observation_count: int = Field(default=0, ge=0)
    initial_state_seed: int = Field(ge=0)


runtime: WorldModelRuntime | None = None
inference_lock = Lock()


def artifact_directory() -> Path:
    return Path(os.getenv(
        "LEAP_MODEL_ARTIFACT_DIR",
        str(Path(__file__).resolve().parents[1] / "backend/model_artifacts"),
    ))


def authorize(authorization: str | None) -> None:
    expected = os.getenv("WORLD_MODEL_SERVICE_TOKEN")
    production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    if production and not expected:
        raise HTTPException(status_code=503, detail="service token is not configured")
    supplied = authorization or ""
    if expected and not hmac.compare_digest(supplied, f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="invalid service token")


@asynccontextmanager
async def lifespan(_: FastAPI):
    global runtime
    runtime = WorldModelRuntime(artifact_directory(), device=os.getenv("WORLD_MODEL_DEVICE", "cpu"))
    yield
    runtime = None


app = FastAPI(title="LEAP World Model", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready" if runtime is not None else "loading"}


@app.get("/model-info")
def model_info(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(authorization)
    if runtime is None:
        raise HTTPException(status_code=503, detail="model is not loaded")
    return runtime.model_info


@app.post("/predict-action")
def predict_action(
    request: PlanRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    authorize(authorization)
    if runtime is None:
        raise HTTPException(status_code=503, detail="model is not loaded")
    with inference_lock:
        return runtime.plan(request.model_dump(mode="json"))
