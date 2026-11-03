"""Server-scored, first-submission assessments kept separate from tutor progress."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .bank import QUESTION_BANK, UNSURE, VERSION, AssessmentQuestion, assessment_task
from .final_bank import FINAL_QUESTION_BANK
from ..database import connect
from ..tutoring.authored_content import STAGES_BY_TASK
from ..tutoring.lesson_code import FIXED_LESSON_CODE
from ..collection.config import assessment_preview_allowed, collection_mode


class AssessmentSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=80)
    answers: dict[str, Annotated[int, Field(strict=True, ge=0, le=3)]] = Field(min_length=10, max_length=10)


AssessmentPhase = Literal["pre", "post"]


def questions_for_phase(task: str, phase: AssessmentPhase) -> tuple[AssessmentQuestion, ...]:
    """Select the independently authored form for this phase."""
    return (QUESTION_BANK if phase == "pre" else FINAL_QUESTION_BANK)[assessment_task(task)]


def _public_result(result: dict, phase: AssessmentPhase) -> dict:
    if phase == "post":
        return result
    # Keep the scored research record on the server, but do not teach the
    # answers through the starting assessment, including its submission response.
    return {**result, "questions": []}


def _outcome(before: dict | None, after: dict) -> str:
    if before is None:
        return "no_baseline"
    if before["correct"]:
        return "kept" if after["correct"] else "slipped"
    return "learned" if after["correct"] else "still_learning"


def _report(task: str, result: dict, baseline: dict | None) -> dict:
    """Pre/post comparison shown only once the final assessment is submitted.

    The two forms are paired item by item on stage and concept, so each final
    question is compared with the starting question at the same position.
    """
    before_items = baseline["questions"] if baseline else []
    items = []
    for index, after in enumerate(result["questions"]):
        before = before_items[index] if index < len(before_items) else None
        if before and (before["stage"], before["concept"]) != (after["stage"], after["concept"]):
            before = None
        items.append({
            "stage": after["stage"], "concept": after["concept"], "after": after["correct"],
            "before": None if before is None else "unsure" if before["options"][before["selected"]] == UNSURE else before["correct"],
            "outcome": _outcome(before, after),
        })
    stages = []
    for stage in FIXED_LESSON_CODE[task]:
        stage_items = [item for item in items if item["stage"] == stage]
        stages.append({
            "stage": stage, "title": str(STAGES_BY_TASK[task][stage]["title"]), "total": len(stage_items),
            "after": sum(item["after"] for item in stage_items),
            "before": sum(item["before"] is True for item in stage_items) if baseline else None,
        })
    outcomes = {key: sum(item["outcome"] == key for item in items) for key in ("learned", "kept", "slipped", "still_learning")}
    return {
        "before_score": baseline["score"] if baseline else None,
        "before_unsure": sum(item["before"] == "unsure" for item in items) if baseline else None,
        "after_score": result["score"], "total": result["total"],
        "outcomes": outcomes, "stages": stages, "concepts": items,
    }


def _with_report(connection, learner_id: str, task: str, result: dict) -> dict:
    baseline_row = connection.execute(
        "SELECT payload FROM task_pre_assessments WHERE learner_id = ? AND task = ? AND version = ?",
        (learner_id, task, VERSION),
    ).fetchone()
    return {**result, "report": _report(task, result, json.loads(baseline_row["payload"]) if baseline_row else None)}


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
        result = json.loads(row["payload"]) if row else None
        if result and phase == "post":
            result = _with_report(connection, learner_id, task, result)
    # Never deliver the answer key (including explanations) before submission.
    questions = [
        {key: value for key, value in asdict(question).items() if key not in {"answer", "explanation"}}
        for question in questions_for_phase(task, phase)
    ] if phase == "pre" or unlocked or assessment_preview_allowed() else []
    return {
        "task": task, "phase": phase, "version": VERSION,
        "unlocked": phase == "pre" or unlocked,
        "preview_allowed": assessment_preview_allowed(),
        "baseline_score": json.loads(baseline_row["payload"])["score"] if baseline_row else None,
        "questions": questions, "result": _public_result(result, phase) if result else None,
    }


def submit_assessment(learner_id: str, task: str, submission: AssessmentSubmission, phase: AssessmentPhase = "post") -> dict:
    task = assessment_task(task)
    if submission.version != VERSION:
        raise ValueError("The assessment has changed. Reload it before submitting.")
    questions = questions_for_phase(task, phase)
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
        saved = json.loads(connection.execute(
            f"SELECT payload FROM {table} WHERE learner_id = ? AND task = ? AND version = ?",
            (learner_id, task, VERSION),
        ).fetchone()["payload"])
        if phase == "post":
            saved = _with_report(connection, learner_id, task, saved)
    return _public_result(saved, phase)
