"""Server-scored, first-submission assessments kept separate from tutor progress."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .bank import QUESTION_BANK, VERSION, assessment_task
from ..database import connect
from ..tutoring.lesson_code import FIXED_LESSON_CODE
from ..collection.config import assessment_preview_allowed, collection_mode


class AssessmentSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=80)
    answers: dict[str, Annotated[int, Field(strict=True, ge=0, le=3)]] = Field(min_length=10, max_length=10)


AssessmentPhase = Literal["pre", "post"]


def _unlocked(connection, learner_id: str, task: str) -> bool:
    row = connection.execute(
        "SELECT completed_stages FROM user_progress WHERE learner_id = ? AND task = ?",
        (learner_id, task),
    ).fetchone()
    return row is not None and row["completed_stages"] >= len(FIXED_LESSON_CODE[task])


def get_assessment(learner_id: str, task: str, phase: AssessmentPhase = "post") -> dict:
    task = assessment_task(task)
    table = "task_pre_assessments" if phase == "pre" else "task_assessments"
    with connect() as connection:
        unlocked = _unlocked(connection, learner_id, task)
        row = connection.execute(
            f"SELECT payload FROM {table} WHERE learner_id = ? AND task = ? AND version = ?",
            (learner_id, task, VERSION),
        ).fetchone()
        baseline_row = connection.execute(
            "SELECT payload FROM task_pre_assessments WHERE learner_id = ? AND task = ? AND version = ?",
            (learner_id, task, VERSION),
        ).fetchone() if phase == "post" else None
    # Never deliver the answer key (including explanations) before submission.
    questions = [
        {key: value for key, value in asdict(question).items() if key not in {"answer", "explanation"}}
        for question in QUESTION_BANK[task]
    ] if phase == "pre" or unlocked or assessment_preview_allowed() else []
    return {
        "task": task, "phase": phase, "version": VERSION,
        "unlocked": phase == "pre" or unlocked,
        "preview_allowed": assessment_preview_allowed(),
        "baseline_score": json.loads(baseline_row["payload"])["score"] if baseline_row else None,
        "questions": questions, "result": json.loads(row["payload"]) if row else None,
    }


def submit_assessment(learner_id: str, task: str, submission: AssessmentSubmission, phase: AssessmentPhase = "post") -> dict:
    task = assessment_task(task)
    if submission.version != VERSION:
        raise ValueError("The assessment has changed. Reload it before submitting.")
    questions = QUESTION_BANK[task]
    if set(submission.answers) != {question.id for question in questions}:
        raise ValueError("Answer all 10 questions from this task's assessment.")
    reviews = [
        {**asdict(question), "selected": submission.answers[question.id],
         "correct": submission.answers[question.id] == question.answer}
        for question in questions
    ]
    result = {
        "task": task, "phase": phase, "version": VERSION,
        "score": sum(item["correct"] for item in reviews), "total": len(questions),
        "submitted_at": datetime.now(timezone.utc).isoformat(), "questions": reviews,
        "collection_mode": collection_mode(),
    }
    with connect() as connection:
        if phase == "post" and not _unlocked(connection, learner_id, task):
            raise PermissionError("Complete all six lesson stages to unlock the final assessment.")
        table = "task_pre_assessments" if phase == "pre" else "task_assessments"
        # Retrying a request or submitting from two tabs cannot overwrite the first score.
        connection.execute(
            f"""INSERT INTO {table} (learner_id, task, version, payload)
            VALUES (?, ?, ?, ?) ON CONFLICT (learner_id, task, version) DO NOTHING""",
            (learner_id, task, VERSION, json.dumps(result)),
        )
        saved = connection.execute(
            f"SELECT payload FROM {table} WHERE learner_id = ? AND task = ? AND version = ?",
            (learner_id, task, VERSION),
        ).fetchone()
    return json.loads(saved["payload"])
