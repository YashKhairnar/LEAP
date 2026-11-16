"""Workshop persistence.

The workshop keeps its data in its own tables, apart from the lesson,
assessment and collection tables:

- workshop_progress:  one row per learner (current stage, completed stages, uploaded file)
- workshop_cell_runs: every cell run, with the code and its output (append-only)
- workshop_answers:   every saved answer to a Check-your-understanding question (append-only)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..database import connect
from .content import STAGE_IDS, WORKSHOP_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_workshop_tables() -> None:
    with connect() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS workshop_progress (
                learner_id TEXT PRIMARY KEY,
                workshop_version TEXT NOT NULL,
                current_stage TEXT NOT NULL,
                completed_stages TEXT NOT NULL,
                uploaded_filename TEXT,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT)"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS workshop_cell_runs (
                run_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                workshop_version TEXT NOT NULL,
                stage_id TEXT NOT NULL,
                cell_id TEXT NOT NULL,
                execution_count INTEGER NOT NULL,
                code TEXT NOT NULL,
                success INTEGER NOT NULL,
                stdout TEXT NOT NULL,
                stderr TEXT NOT NULL,
                result TEXT,
                table_preview TEXT,
                duration_ms INTEGER NOT NULL,
                engine TEXT NOT NULL,
                uploaded_filename TEXT,
                created_at TEXT NOT NULL)"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS workshop_cell_runs_learner ON workshop_cell_runs (learner_id, created_at)"
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS workshop_answers (
                answer_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                workshop_version TEXT NOT NULL,
                stage_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT NOT NULL)"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS workshop_answers_learner ON workshop_answers (learner_id, created_at)"
        )


def _progress_row(connection: Any, learner_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT current_stage, completed_stages, uploaded_filename, started_at, updated_at, completed_at "
        "FROM workshop_progress WHERE learner_id = ?", (learner_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def get_progress(learner_id: str) -> dict[str, Any]:
    with connect() as connection:
        row = _progress_row(connection, learner_id)
    if row is None:
        return {"current_stage": STAGE_IDS[0], "completed_stages": [], "uploaded_filename": None,
                "started_at": None, "updated_at": None, "completed_at": None}
    return {**row, "completed_stages": json.loads(row["completed_stages"])}


def _ensure_progress(connection: Any, learner_id: str) -> dict[str, Any]:
    row = _progress_row(connection, learner_id)
    if row is not None:
        return {**row, "completed_stages": json.loads(row["completed_stages"])}
    now = _now()
    connection.execute(
        "INSERT INTO workshop_progress (learner_id, workshop_version, current_stage, completed_stages, started_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (learner_id) DO NOTHING",
        (learner_id, WORKSHOP_VERSION, STAGE_IDS[0], "[]", now, now),
    )
    row = _progress_row(connection, learner_id)
    return {**row, "completed_stages": json.loads(row["completed_stages"])}


def save_cell_run(learner_id: str, stage_id: str, cell_id: str, code: str, result: dict[str, Any],
                  uploaded_filename: str | None) -> dict[str, Any]:
    """Store one run and return it with its notebook-style execution count."""
    run_id = str(uuid4())
    created_at = _now()
    with connect() as connection:
        _ensure_progress(connection, learner_id)
        count_row = connection.execute(
            "SELECT COUNT(*) AS runs FROM workshop_cell_runs WHERE learner_id = ?", (learner_id,),
        ).fetchone()
        execution_count = int(dict(count_row)["runs"]) + 1
        connection.execute(
            "INSERT INTO workshop_cell_runs (run_id, learner_id, workshop_version, stage_id, cell_id, execution_count, code, "
            "success, stdout, stderr, result, table_preview, duration_ms, engine, uploaded_filename, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, learner_id, WORKSHOP_VERSION, stage_id, cell_id, execution_count, code,
             1 if result["success"] else 0, result["stdout"], result["stderr"],
             json.dumps(result["result"]), json.dumps(result["table_preview"]), result["duration_ms"],
             result["engine"], uploaded_filename, created_at),
        )
        if cell_id == "upload" and result["success"] and uploaded_filename:
            connection.execute(
                "UPDATE workshop_progress SET uploaded_filename = ?, updated_at = ? WHERE learner_id = ?",
                (uploaded_filename, created_at, learner_id),
            )
        else:
            connection.execute("UPDATE workshop_progress SET updated_at = ? WHERE learner_id = ?", (created_at, learner_id))
    return {"run_id": run_id, "cell_id": cell_id, "execution_count": execution_count, "created_at": created_at,
            "code": code, **result}


def latest_cell_runs(learner_id: str) -> dict[str, dict[str, Any]]:
    """For each cell: the latest run (for display) and the latest successful run (for unlocking)."""
    with connect() as connection:
        rows = connection.execute(
            "SELECT run_id, cell_id, execution_count, code, success, stdout, stderr, result, table_preview, "
            "duration_ms, engine, created_at FROM workshop_cell_runs WHERE learner_id = ? "
            "ORDER BY execution_count", (learner_id,),
        ).fetchall()
    cells: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        run = {
            **row,
            "success": bool(row["success"]),
            "result": json.loads(row["result"]) if row["result"] else None,
            "table_preview": json.loads(row["table_preview"]) if row["table_preview"] else None,
            "plots": [],
        }
        entry = cells.setdefault(row["cell_id"], {"latest": None, "latest_success": None})
        entry["latest"] = run
        if run["success"]:
            entry["latest_success"] = run
    return cells


def save_answer(learner_id: str, stage_id: str, question_id: str, answer: str) -> dict[str, Any]:
    created_at = _now()
    with connect() as connection:
        _ensure_progress(connection, learner_id)
        connection.execute(
            "INSERT INTO workshop_answers (answer_id, learner_id, workshop_version, stage_id, question_id, answer, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid4()), learner_id, WORKSHOP_VERSION, stage_id, question_id, answer, created_at),
        )
        connection.execute("UPDATE workshop_progress SET updated_at = ? WHERE learner_id = ?", (created_at, learner_id))
    return {"question_id": question_id, "answer": answer, "saved_at": created_at}


def latest_answers(learner_id: str) -> dict[str, dict[str, str]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT question_id, answer, created_at FROM workshop_answers WHERE learner_id = ? ORDER BY created_at",
            (learner_id,),
        ).fetchall()
    return {dict(row)["question_id"]: {"answer": dict(row)["answer"], "saved_at": dict(row)["created_at"]} for row in rows}


def complete_stage(learner_id: str, stage_id: str, next_stage: str, workshop_complete: bool) -> dict[str, Any]:
    now = _now()
    with connect() as connection:
        progress = _ensure_progress(connection, learner_id)
        completed = list(progress["completed_stages"])
        if stage_id not in completed:
            completed.append(stage_id)
        # Moving forward only: revisiting an earlier stage never pulls the learner back.
        current = progress["current_stage"]
        if STAGE_IDS.index(next_stage) > STAGE_IDS.index(current):
            current = next_stage
        connection.execute(
            "UPDATE workshop_progress SET completed_stages = ?, current_stage = ?, updated_at = ?, "
            "completed_at = COALESCE(completed_at, ?) WHERE learner_id = ?",
            (json.dumps(completed), current, now, now if workshop_complete else None, learner_id),
        )
    return get_progress(learner_id)
