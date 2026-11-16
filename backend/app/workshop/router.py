"""HTTP API for the Colab workshop, mounted under /api/workshop."""

# No `from __future__ import annotations`: FastAPI must resolve the local `User` alias at runtime.
import os
from typing import Annotated, Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..models import UserRecord
from . import store
from .content import (
    CELLS,
    LEARNING_STAGES,
    QUESTIONS,
    QUESTIONS_BY_ID,
    STAGES,
    STAGE_IDS,
    WORKSHOP_ID,
    WORKSHOP_TITLE,
    WORKSHOP_VERSION,
    cell as workshop_cell,
    next_stage_id,
    own_reviews_written,
    stage as workshop_stage,
)
from .runner import DATASET_PATH, run_workshop_cell, valid_upload_name


class UploadedFile(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    size: int = Field(ge=0)


class CellRunRequest(BaseModel):
    code: str = Field(min_length=1, max_length=8000)
    uploaded_file: Optional[UploadedFile] = None


class AnswerRequest(BaseModel):
    answer: str = Field(max_length=5000)


class EnterRequest(BaseModel):
    research_id: str = Field(min_length=1, max_length=64)


def stage_unlocked(progress: dict[str, Any], stage_id: str) -> bool:
    return stage_id in progress["completed_stages"] or stage_id == progress["current_stage"]


def cell_done(runs: dict[str, dict[str, Any]], cell_id: str) -> bool:
    success = runs.get(cell_id, {}).get("latest_success")
    if success is None:
        return False
    return workshop_cell(cell_id).kind != "own_reviews" or own_reviews_written(success["code"])


def missing_for_stage(stage_id: str, runs: dict[str, dict[str, Any]], answers: dict[str, dict[str, str]]) -> list[str]:
    stage = workshop_stage(stage_id)
    missing = [f"Run {item.label}: {item.title}" for item in stage.cells if not cell_done(runs, item.cell_id)]
    missing += [f"Answer {question.question_id}" for question in stage.questions
                if not answers.get(question.question_id, {}).get("answer", "").strip()]
    return missing


def workshop_state(learner_id: str) -> dict[str, Any]:
    progress = store.get_progress(learner_id)
    runs = store.latest_cell_runs(learner_id)
    answers = store.latest_answers(learner_id)
    return {
        "workshop_id": WORKSHOP_ID,
        "version": WORKSHOP_VERSION,
        "research_id": store.research_id_for(learner_id),
        "current_stage": progress["current_stage"],
        "completed_stages": progress["completed_stages"],
        "uploaded_filename": progress["uploaded_filename"],
        "workshop_complete": all(item.stage_id in progress["completed_stages"] for item in LEARNING_STAGES),
        "started_at": progress["started_at"],
        "updated_at": progress["updated_at"],
        "cells": {
            cell_id: {"done": cell_done(runs, cell_id), "latest": entry["latest"]}
            for cell_id, entry in runs.items()
        },
        "answers": answers,
        "cells_done": sum(1 for item in CELLS if item.stage_id != "start" and cell_done(runs, item.cell_id)),
        "cells_total": sum(1 for item in CELLS if item.stage_id != "start"),
        "answers_done": sum(1 for item in QUESTIONS if answers.get(item.question_id, {}).get("answer", "").strip()),
        "answers_total": len(QUESTIONS),
    }


def build_workshop_router(
    current_user: Callable[..., UserRecord],
    set_session_cookie: Callable[[Response, str], None] = lambda response, token: None,
) -> APIRouter:
    router = APIRouter(prefix="/api/workshop", tags=["workshop"])
    User = Annotated[UserRecord, Depends(current_user)]

    @router.post("/enter")
    def enter(request: EnterRequest, response: Response) -> dict[str, Any]:
        """Enter the workshop with a research ID only (no account or password)."""
        try:
            session, research_id = store.enter_with_research_id(request.research_id)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        set_session_cookie(response, session.access_token)
        return {"user": session.user.model_dump(), "research_id": research_id}

    @router.get("/content")
    def content(_: User) -> dict[str, Any]:
        return {
            "workshop_id": WORKSHOP_ID,
            "version": WORKSHOP_VERSION,
            "title": WORKSHOP_TITLE,
            "dataset": {"filename": "dataset.csv", "bytes": DATASET_PATH.stat().st_size, "header": "text,sentiment"},
            "post_survey_url": os.getenv("WORKSHOP_POST_SURVEY_URL") or None,
            "stages": [item.public() for item in STAGES],
        }

    @router.get("/state")
    def state(user: User) -> dict[str, Any]:
        return workshop_state(user.user_id)

    @router.get("/dataset.csv")
    def dataset(_: User) -> FileResponse:
        return FileResponse(DATASET_PATH, media_type="text/csv", filename="dataset.csv")

    @router.post("/cells/{cell_id}/run")
    def run_cell(cell_id: str, request: CellRunRequest, user: User) -> dict[str, Any]:
        try:
            target = workshop_cell(cell_id)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        progress = store.get_progress(user.user_id)
        if not stage_unlocked(progress, target.stage_id):
            raise HTTPException(status_code=403, detail="Finish the earlier steps first.")
        runs = store.latest_cell_runs(user.user_id)
        stage_cells = workshop_stage(target.stage_id).cells
        for earlier in stage_cells[: stage_cells.index(target)]:
            if not runs.get(earlier.cell_id, {}).get("latest_success"):
                raise HTTPException(status_code=409, detail=f"Run {earlier.label} ({earlier.title}) first.")

        uploaded_filename = progress["uploaded_filename"]
        if target.kind == "upload":
            upload = request.uploaded_file
            if upload is None:
                raise HTTPException(status_code=422, detail="Choose the dataset file to upload.")
            if not valid_upload_name(upload.name) or upload.size != DATASET_PATH.stat().st_size:
                raise HTTPException(status_code=422, detail="That file isn't the workshop's dataset.csv.")
            uploaded_filename = upload.name

        result = run_workshop_cell(cell_id, request.code, uploaded_filename)
        saved = store.save_cell_run(user.user_id, target.stage_id, cell_id, request.code, result,
                                    uploaded_filename if target.kind == "upload" else None)
        return {**saved, "done": result["success"] and (target.kind != "own_reviews" or own_reviews_written(request.code))}

    @router.put("/answers/{question_id}")
    def answer(question_id: str, request: AnswerRequest, user: User) -> dict[str, Any]:
        question = QUESTIONS_BY_ID.get(question_id)
        if question is None:
            raise HTTPException(status_code=404, detail=f"unknown workshop question: {question_id}")
        if not stage_unlocked(store.get_progress(user.user_id), question.stage_id):
            raise HTTPException(status_code=403, detail="Finish the earlier steps first.")
        return store.save_answer(user.user_id, question.stage_id, question_id, request.answer)

    @router.post("/stages/{stage_id}/complete")
    def complete(stage_id: str, user: User) -> dict[str, Any]:
        if stage_id not in STAGE_IDS or stage_id == STAGE_IDS[-1]:
            raise HTTPException(status_code=404, detail=f"unknown workshop stage: {stage_id}")
        progress = store.get_progress(user.user_id)
        if not stage_unlocked(progress, stage_id):
            raise HTTPException(status_code=403, detail="Finish the earlier steps first.")
        missing = missing_for_stage(stage_id, store.latest_cell_runs(user.user_id), store.latest_answers(user.user_id))
        if missing:
            raise HTTPException(status_code=409, detail={"message": "This step isn't finished yet.", "missing": missing})
        last = stage_id == LEARNING_STAGES[-1].stage_id
        store.complete_stage(user.user_id, stage_id, next_stage_id(stage_id), last)
        return workshop_state(user.user_id)

    return router
