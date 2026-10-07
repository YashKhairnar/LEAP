import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # PostgreSQL support is installed in production.
    psycopg = None
    dict_row = None

from .auth import hash_password, new_access_token, token_digest, verify_password
from .paths import BACKEND_ROOT
from .models import (
    AuthResponse,
    BehaviorEventCreate,
    BehaviorEventRecord,
    CodeExecutionRequest,
    CodeExecutionResult,
    ContentCreate,
    ContentRecord,
    InteractionCreate,
    ProgressRecord,
    TransitionCreate,
    TransitionRecord,
    TutorGenerationRequest,
    TutorGenerationResponse,
    TutorQuestionState,
    TutorResumeResponse,
    UserRecord,
)

DEFAULT_DATABASE = BACKEND_ROOT / "data" / "leap.db"
IntegrityErrors = (sqlite3.IntegrityError,) if psycopg is None else (sqlite3.IntegrityError, psycopg.IntegrityError)


def database_path() -> Path:
    return Path(os.getenv("LEAP_DATABASE_PATH", str(DEFAULT_DATABASE)))


class DatabaseConnection:
    def __init__(self, connection: Any, postgres: bool) -> None:
        self.raw = connection
        self.postgres = postgres

    def execute(self, query: str, parameters: tuple = ()):
        if self.postgres:
            query = query.replace("?", "%s").replace("BEGIN IMMEDIATE", "BEGIN")
        return self.raw.execute(query, parameters)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        if exception_type is None:
            self.raw.commit()
        else:
            self.raw.rollback()
        self.raw.close()


def connect() -> DatabaseConnection:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if psycopg is None:
            raise RuntimeError("DATABASE_URL requires psycopg; install backend requirements")
        return DatabaseConnection(psycopg.connect(database_url, row_factory=dict_row), True)
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return DatabaseConnection(connection, False)


def initialize_database() -> None:
    with connect() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS task_assessments (
                learner_id TEXT NOT NULL,
                task TEXT NOT NULL,
                version TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (learner_id, task, version))"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS task_pre_assessments (
                learner_id TEXT NOT NULL,
                task TEXT NOT NULL,
                version TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (learner_id, task, version))"""
        )
        connection.execute(
        """
        CREATE TABLE IF NOT EXISTS transitions (
            transition_id TEXT PRIMARY KEY,
            learner_id TEXT,
            session_id TEXT,
            sequence_index INTEGER,
            payload TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(learner_id, session_id, sequence_index)
        )
        """
        )
        connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            participant_code TEXT NOT NULL UNIQUE,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            java_experience TEXT NOT NULL,
            consent_version TEXT NOT NULL,
            consented_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        connection.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        connection.execute(
        """
        CREATE TABLE IF NOT EXISTS behavior_events (
            event_id TEXT PRIMARY KEY,
            learner_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            sequence_index INTEGER NOT NULL,
            payload TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(learner_id, session_id, sequence_index)
        )
        """
        )
        connection.execute(
        """
        CREATE TABLE IF NOT EXISTS content_items (
            content_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS session_sequences (
                learner_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                last_sequence INTEGER NOT NULL,
                PRIMARY KEY(learner_id, session_id)
            )
            """
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS user_progress (
                learner_id TEXT NOT NULL, task TEXT NOT NULL,
                completed_stages INTEGER NOT NULL DEFAULT 0,
                total_stages INTEGER NOT NULL DEFAULT 6,
                task_complete INTEGER NOT NULL DEFAULT 0,
                current_stage TEXT,
                current_step TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(learner_id, task))"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS code_executions (
                execution_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                sequence_index INTEGER NOT NULL,
                task TEXT NOT NULL,
                stage TEXT NOT NULL,
                step TEXT NOT NULL,
                success INTEGER NOT NULL,
                code TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(learner_id, session_id, sequence_index))"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS tutor_stage_lessons (
                learner_id TEXT NOT NULL,
                task TEXT NOT NULL,
                stage TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (learner_id, task, stage))"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS tutor_question_instances (
                content_instance_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                task TEXT NOT NULL,
                stage TEXT NOT NULL,
                step TEXT NOT NULL,
                action_type TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                presentation_id TEXT,
                latest_answer TEXT,
                latest_correct INTEGER,
                latest_attempt INTEGER NOT NULL DEFAULT 1,
                payload TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"""
        )
        connection.execute(
            """CREATE INDEX IF NOT EXISTS tutor_question_location
            ON tutor_question_instances (learner_id, task, stage, step, active, created_at)"""
        )
        connection.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS tutor_one_active_question
            ON tutor_question_instances (learner_id, task, stage, step)
            WHERE active = 1"""
        )
        if not connection.postgres:
            transition_columns = {row["name"] for row in connection.execute("PRAGMA table_info(transitions)").fetchall()}
            for column, column_type in (("learner_id", "TEXT"), ("session_id", "TEXT"), ("sequence_index", "INTEGER")):
                if column not in transition_columns:
                    connection.execute(f"ALTER TABLE transitions ADD COLUMN {column} {column_type}")
            user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
            if "participant_code" not in user_columns:
                connection.execute("ALTER TABLE users ADD COLUMN participant_code TEXT")
                rows = connection.execute("SELECT user_id FROM users").fetchall()
                for row in rows:
                    connection.execute(
                        "UPDATE users SET participant_code = ? WHERE user_id = ?",
                        (_new_participant_code(), row["user_id"]),
                    )
            if "consent_version" not in user_columns:
                connection.execute("ALTER TABLE users ADD COLUMN consent_version TEXT NOT NULL DEFAULT 'legacy'")
            if "consented_at" not in user_columns:
                connection.execute("ALTER TABLE users ADD COLUMN consented_at TIMESTAMP")
            user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
            if "email" in user_columns or "name" in user_columns:
                connection.execute(
                    """CREATE TABLE users_anonymous (
                        user_id TEXT PRIMARY KEY,
                        participant_code TEXT NOT NULL UNIQUE,
                        password_salt TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        java_experience TEXT NOT NULL,
                        consent_version TEXT NOT NULL,
                        consented_at TIMESTAMP,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )"""
                )
                connection.execute(
                    """INSERT INTO users_anonymous
                    (user_id, participant_code, password_salt, password_hash, java_experience,
                     consent_version, consented_at, created_at)
                    SELECT user_id, participant_code, password_salt, password_hash, java_experience,
                           consent_version, consented_at, created_at FROM users"""
                )
                connection.execute("DROP TABLE users")
                connection.execute("ALTER TABLE users_anonymous RENAME TO users")
            auth_columns = {row["name"] for row in connection.execute("PRAGMA table_info(auth_sessions)").fetchall()}
            # Run after the legacy anonymous-account migration, which rebuilds users.
            user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
            if "analogy_preference" not in user_columns:
                connection.execute("ALTER TABLE users ADD COLUMN analogy_preference TEXT NOT NULL DEFAULT 'java'")
            if "expires_at" not in auth_columns:
                connection.execute("ALTER TABLE auth_sessions ADD COLUMN expires_at TIMESTAMP")
            progress_columns = {row["name"] for row in connection.execute("PRAGMA table_info(user_progress)").fetchall()}
            if "current_stage" not in progress_columns:
                connection.execute("ALTER TABLE user_progress ADD COLUMN current_stage TEXT")
            if "current_step" not in progress_columns:
                connection.execute("ALTER TABLE user_progress ADD COLUMN current_step TEXT")
            question_columns = {row["name"] for row in connection.execute("PRAGMA table_info(tutor_question_instances)").fetchall()}
            for column, column_type in (
                ("presentation_id", "TEXT"), ("latest_answer", "TEXT"),
                ("latest_correct", "INTEGER"), ("latest_attempt", "INTEGER NOT NULL DEFAULT 1"),
                ("action_type", "TEXT"),
            ):
                if column not in question_columns:
                    connection.execute(f"ALTER TABLE tutor_question_instances ADD COLUMN {column} {column_type}")
        else:
            connection.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS analogy_preference TEXT NOT NULL DEFAULT 'java'")
            connection.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS participant_code TEXT")
            rows = connection.execute(
                "SELECT user_id FROM users WHERE participant_code IS NULL"
            ).fetchall()
            for row in rows:
                connection.execute(
                    "UPDATE users SET participant_code = ? WHERE user_id = ?",
                    (_new_participant_code(), row["user_id"]),
                )
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS users_participant_code ON users (participant_code)"
            )
            connection.execute("ALTER TABLE users ALTER COLUMN participant_code SET NOT NULL")
            connection.execute("ALTER TABLE users DROP COLUMN IF EXISTS email")
            connection.execute("ALTER TABLE users DROP COLUMN IF EXISTS name")
            connection.execute("ALTER TABLE user_progress ADD COLUMN IF NOT EXISTS current_stage TEXT")
            connection.execute("ALTER TABLE user_progress ADD COLUMN IF NOT EXISTS current_step TEXT")
            connection.execute("ALTER TABLE tutor_question_instances ADD COLUMN IF NOT EXISTS presentation_id TEXT")
            connection.execute("ALTER TABLE tutor_question_instances ADD COLUMN IF NOT EXISTS latest_answer TEXT")
            connection.execute("ALTER TABLE tutor_question_instances ADD COLUMN IF NOT EXISTS latest_correct INTEGER")
            connection.execute("ALTER TABLE tutor_question_instances ADD COLUMN IF NOT EXISTS latest_attempt INTEGER NOT NULL DEFAULT 1")
            connection.execute("ALTER TABLE tutor_question_instances ADD COLUMN IF NOT EXISTS action_type TEXT")


def _created_at(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _new_participant_code() -> str:
    return f"LP-{secrets.token_hex(6).upper()}"


def _user_record(row: Any) -> UserRecord:
    return UserRecord(
        user_id=row["user_id"], participant_code=row["participant_code"],
        java_experience=row["java_experience"], analogy_preference=row["analogy_preference"]
    )


def create_user(user_id: str, password: str, java_experience: str, consent_version: str, analogy_preference: str = "java") -> AuthResponse:
    salt, password_hash = hash_password(password)
    token = new_access_token()
    participant_code = _new_participant_code()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    with connect() as connection:
        connection.execute(
            "INSERT INTO users (user_id, participant_code, password_salt, password_hash, java_experience, consent_version, analogy_preference) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, participant_code, salt, password_hash, java_experience, consent_version, analogy_preference),
        )
        connection.execute(
            "INSERT INTO auth_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_digest(token), user_id, expires_at),
        )
        row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return AuthResponse(access_token=token, user=_user_record(row))


def authenticate_user(participant_code: str, password: str) -> Optional[AuthResponse]:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE participant_code = ?", (participant_code,)
        ).fetchone()
        if row is None or not verify_password(password, row["password_salt"], row["password_hash"]):
            return None
        token = new_access_token()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        connection.execute(
            "INSERT INTO auth_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_digest(token), row["user_id"], expires_at),
        )
    return AuthResponse(access_token=token, user=_user_record(row))


def user_for_token(token: str) -> Optional[UserRecord]:
    with connect() as connection:
        row = connection.execute(
            "SELECT users.* FROM auth_sessions JOIN users ON users.user_id = auth_sessions.user_id WHERE auth_sessions.token_hash = ? AND auth_sessions.expires_at > CURRENT_TIMESTAMP",
            (token_digest(token),),
        ).fetchone()
    return _user_record(row) if row else None


def revoke_token(token: str) -> None:
    with connect() as connection:
        connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_digest(token),))


def _next_sequence(connection: DatabaseConnection, learner_id: str, session_id: str) -> int:
    row = connection.execute(
        """INSERT INTO session_sequences (learner_id, session_id, last_sequence)
        VALUES (?, ?, 0)
        ON CONFLICT (learner_id, session_id)
        DO UPDATE SET last_sequence = session_sequences.last_sequence + 1
        RETURNING last_sequence""",
        (learner_id, session_id),
    ).fetchone()
    return int(row["last_sequence"] if isinstance(row, dict) or hasattr(row, "keys") else row[0])


def save_interaction(interaction: InteractionCreate, learner_id: str) -> TransitionRecord:
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        content_payload = interaction.content.model_dump(mode="json")
        content_payload["planner_decision"] = _collection_planner_decision(content_payload.get("planner_decision"))
        encoded_content = json.dumps(content_payload, sort_keys=True)
        existing = connection.execute(
            "SELECT payload FROM content_items WHERE content_id = ?", (interaction.content.content_id,)
        ).fetchone()
        if existing is not None:
            stored = json.loads(existing["payload"])
            # Old clients reconstructed provenance on resume. Preserve the original
            # provenance, but still reject any change to the actual question/lesson.
            core = lambda value: {k: v for k, v in value.items() if k not in {"planner_decision", "generation_metadata"}}
            if core(stored) != core(content_payload):
                raise ValueError("content_id already exists with different content")
            content_payload = stored
        if existing is None:
            connection.execute(
                "INSERT INTO content_items (content_id, payload) VALUES (?, ?)",
                (interaction.content.content_id, encoded_content),
            )
        sequence_index = _next_sequence(connection, learner_id, interaction.session_id)
        payload = {
            "schema_version": "2.1",
            "transition_id": interaction.transition_id,
            "learner_id": learner_id,
            "session_id": interaction.session_id,
            "sequence_index": sequence_index,
            "location_before": interaction.location_before.model_dump(mode="json"),
            "instructional_action": interaction.instructional_action.model_dump(mode="json"),
            "learner_action": interaction.learner_action.model_dump(mode="json"),
            "observation": interaction.observation.model_dump(mode="json"),
            "progression": interaction.progression.model_dump(mode="json"),
            "location_after": interaction.location_after.model_dump(mode="json"),
            "event_timestamp": interaction.event_timestamp.isoformat(),
            "selection_policy": (content_payload.get("planner_decision") or {}).get("assignment_policy", interaction.selection_policy),
            "presentation_id": interaction.presentation_id,
            # WM state/predictions are not collection outcomes or training targets.
            # Keep the field for schema compatibility, but never persist client-supplied values.
            "learner_state": None,
            "collection_mode": (content_payload.get("generation_metadata") or {}).get("collection_mode", "legacy_unknown"),
        }
        connection.execute(
            "INSERT INTO transitions (transition_id, learner_id, session_id, sequence_index, payload) VALUES (?, ?, ?, ?, ?)",
            (interaction.transition_id, learner_id, interaction.session_id, sequence_index, json.dumps(payload)),
        )
        content_instance_id = (content_payload.get("generation_metadata") or {}).get("content_instance_id")
        if content_instance_id:
            connection.execute(
                """UPDATE tutor_question_instances
                SET latest_answer = ?, latest_correct = ?, latest_attempt = ?
                WHERE content_instance_id = ? AND learner_id = ?""",
                (str(interaction.learner_action.response), int(interaction.observation.correct),
                 interaction.observation.attempt, str(content_instance_id), learner_id),
            )
        row = connection.execute(
            "SELECT payload, created_at FROM transitions WHERE transition_id = ?", (interaction.transition_id,)
        ).fetchone()
    return TransitionRecord(**json.loads(row["payload"]), created_at=_created_at(row["created_at"]))


def _resume_location(event: BehaviorEventCreate) -> tuple[str, str]:
    stage = event.location.stage
    step = event.location.step
    direction = event.data.get("direction") if event.event_type == "navigation" else None
    if direction in {"continue", "direct", "previous"} and event.data.get("to_step"):
        step = str(event.data["to_step"])
    elif direction == "complete_stage" and event.data.get("to_stage"):
        stage = str(event.data["to_stage"])
        step = "connect"
    return stage, step


def save_behavior_event(event: BehaviorEventCreate, learner_id: str) -> BehaviorEventRecord:
    from .collection.config import collection_mode
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        sequence_index = _next_sequence(connection, learner_id, event.session_id)
        payload = event.model_dump(mode="json")
        payload["collection_mode"] = collection_mode()
        connection.execute(
            "INSERT INTO behavior_events (event_id, learner_id, session_id, sequence_index, payload) VALUES (?, ?, ?, ?, ?)",
            (event.event_id, learner_id, event.session_id, sequence_index, json.dumps(payload)),
        )
        if event.event_type == "content_exposure":
            # Visibility/hint events describe exposure, not a navigation decision.
            row = connection.execute("SELECT created_at FROM behavior_events WHERE event_id = ?", (event.event_id,)).fetchone()
            return BehaviorEventRecord(**payload, learner_id=learner_id, sequence_index=sequence_index, created_at=_created_at(row["created_at"]))
        if event.event_type == "content_presented":
            metadata = event.data.get("generation_metadata") or {}
            content_instance_id = metadata.get("content_instance_id")
            presentation_id = event.data.get("presentation_id")
            if content_instance_id and presentation_id:
                connection.execute(
                    """UPDATE tutor_question_instances SET presentation_id = ?
                    WHERE content_instance_id = ? AND learner_id = ?""",
                    (str(presentation_id), str(content_instance_id), learner_id),
                )
        direction = event.data.get("direction") if event.event_type == "navigation" else None
        current_stage, current_step = _resume_location(event)
        connection.execute(
            """INSERT INTO user_progress
            (learner_id, task, completed_stages, total_stages, task_complete, current_stage, current_step)
            VALUES (?, ?, 0, 6, 0, ?, ?)
            ON CONFLICT (learner_id, task) DO UPDATE SET
                current_stage = excluded.current_stage,
                current_step = excluded.current_step,
                updated_at = CURRENT_TIMESTAMP""",
            (learner_id, event.location.task, current_stage, current_step),
        )
        if direction in {"complete_stage", "complete_task"}:
            completed_stages = int(event.data.get("completed_stages", 6 if direction == "complete_task" else 1))
            total_stages = int(event.data.get("total_stages", 6))
            greatest = "GREATEST" if connection.postgres else "MAX"
            connection.execute(
                f"""INSERT INTO user_progress (learner_id, task, completed_stages, total_stages, task_complete)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (learner_id, task) DO UPDATE SET
                    completed_stages = {greatest}(user_progress.completed_stages, excluded.completed_stages),
                    total_stages = excluded.total_stages,
                    task_complete = {greatest}(user_progress.task_complete, excluded.task_complete),
                    updated_at = CURRENT_TIMESTAMP""",
                (learner_id, event.location.task, completed_stages, total_stages, int(direction == "complete_task")),
            )
        row = connection.execute(
            "SELECT created_at FROM behavior_events WHERE event_id = ?", (event.event_id,)
        ).fetchone()
    return BehaviorEventRecord(**payload, learner_id=learner_id, sequence_index=sequence_index, created_at=_created_at(row["created_at"]))


def list_progress(learner_id: str) -> List[ProgressRecord]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT task, completed_stages, total_stages, task_complete, current_stage, current_step, updated_at FROM user_progress WHERE learner_id = ?",
            (learner_id,),
        ).fetchall()
        if not rows:
            events = connection.execute(
                "SELECT payload FROM behavior_events WHERE learner_id = ? ORDER BY sequence_index",
                (learner_id,),
            ).fetchall()
            stage_order = {"data_loading_and_preparation": 1, "train_test_split": 2, "tfidf_vectorization": 3, "model_training": 4, "prediction": 5, "evaluation": 6}
            reconstructed: dict[str, tuple[int, int, bool]] = {}
            for event_row in events:
                payload = json.loads(event_row["payload"])
                data = payload.get("data", {})
                direction = data.get("direction")
                if direction not in {"complete_stage", "complete_task"}:
                    continue
                task = payload.get("location", {}).get("task")
                if not task:
                    continue
                complete = direction == "complete_task"
                completed = int(data.get("completed_stages", 6 if complete else stage_order.get(data.get("from_stage"), 1)))
                previous = reconstructed.get(task, (0, 6, False))
                reconstructed[task] = (max(previous[0], completed), int(data.get("total_stages", 6)), previous[2] or complete)
            for task, (completed, total, complete) in reconstructed.items():
                connection.execute(
                    "INSERT INTO user_progress (learner_id, task, completed_stages, total_stages, task_complete) VALUES (?, ?, ?, ?, ?)",
                    (learner_id, task, completed, total, int(complete)),
                )
            if reconstructed:
                rows = connection.execute(
                    "SELECT task, completed_stages, total_stages, task_complete, current_stage, current_step, updated_at FROM user_progress WHERE learner_id = ?",
                    (learner_id,),
                ).fetchall()
        if any(row["current_stage"] is None or row["current_step"] is None for row in rows):
            event_rows = connection.execute(
                "SELECT payload FROM behavior_events WHERE learner_id = ? ORDER BY sequence_index",
                (learner_id,),
            ).fetchall()
            latest_locations: dict[str, tuple[str, str]] = {}
            for event_row in event_rows:
                event = BehaviorEventCreate.model_validate(json.loads(event_row["payload"]))
                latest_locations[event.location.task] = _resume_location(event)
            for task, (stage, step) in latest_locations.items():
                connection.execute(
                    """UPDATE user_progress SET current_stage = ?, current_step = ?,
                    updated_at = CURRENT_TIMESTAMP WHERE learner_id = ? AND task = ?""",
                    (stage, step, learner_id, task),
                )
            if latest_locations:
                rows = connection.execute(
                    "SELECT task, completed_stages, total_stages, task_complete, current_stage, current_step, updated_at FROM user_progress WHERE learner_id = ?",
                    (learner_id,),
                ).fetchall()
    return [ProgressRecord(task=row["task"], completed_stages=row["completed_stages"], total_stages=row["total_stages"], task_complete=bool(row["task_complete"]), current_stage=row["current_stage"], current_step=row["current_step"], updated_at=_created_at(row["updated_at"])) for row in rows]


def list_session_observations(learner_id: str, session_id: str) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT payload FROM transitions WHERE learner_id = ? AND session_id = ? ORDER BY sequence_index",
            (learner_id, session_id),
        ).fetchall()
    return [json.loads(row["payload"])["observation"] | {
        "response": json.loads(row["payload"])["learner_action"]["response"]
    } for row in rows]


def list_successful_cells(learner_id: str, session_id: str, task: str) -> list[str]:
    with connect() as connection:
        rows = connection.execute(
            """SELECT code FROM (
                SELECT code, sequence_index FROM code_executions
                WHERE learner_id = ? AND session_id = ? AND task = ? AND success = 1
                ORDER BY sequence_index DESC LIMIT 20
            ) recent ORDER BY sequence_index""",
            (learner_id, session_id, task),
        ).fetchall()
    return [str(row["code"]) for row in rows]


def saved_stage_lesson(learner_id: str, task: str, stage: str, prompt_version: str) -> Optional[dict[str, Any]]:
    with connect() as connection:
        row = connection.execute(
            """SELECT payload FROM tutor_stage_lessons
            WHERE learner_id = ? AND task = ? AND stage = ?""",
            (learner_id, task, stage),
        ).fetchone()
    if not row:
        return None
    payload = json.loads(row["payload"])
    if payload.get("prompt_version") != prompt_version:
        return None
    return payload.get("lesson")


def save_generated_tutor_content(
    context: TutorGenerationRequest,
    generated: TutorGenerationResponse,
    learner_id: str,
) -> None:
    if generated.collection_content is None:
        generated.collection_content = collection_content(context, generated)
    lesson_payload = json.dumps({
        "prompt_version": generated.prompt_version,
        "analogy_preference": context.analogy_preference,
        "lesson": generated.lesson.model_dump(mode="json"),
    })
    response_payload = json.dumps(generated.model_dump(mode="json"))
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO content_items (content_id, payload) VALUES (?, ?) ON CONFLICT (content_id) DO NOTHING",
            (generated.collection_content.content_id, json.dumps(generated.collection_content.model_dump(mode="json"))),
        )
        connection.execute(
            """INSERT INTO tutor_stage_lessons (learner_id, task, stage, payload)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (learner_id, task, stage) DO UPDATE SET
                payload = excluded.payload,
                updated_at = CURRENT_TIMESTAMP""",
            (learner_id, context.task, context.stage, lesson_payload),
        )
        connection.execute(
            """UPDATE tutor_question_instances SET active = 0
            WHERE learner_id = ? AND task = ? AND stage = ? AND step = ? AND active = 1""",
            (learner_id, context.task, context.stage, context.step),
        )
        connection.execute(
            """INSERT INTO tutor_question_instances
            (content_instance_id, learner_id, task, stage, step, action_type, active, payload)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                generated.content_instance_id, learner_id, context.task,
                context.stage, context.step, context.action_type.value, response_payload,
            ),
        )


def collection_content(context: TutorGenerationRequest, generated: TutorGenerationResponse) -> ContentCreate:
    from .collection.config import collection_mode
    decision = _collection_planner_decision(context.planner_decision)
    return ContentCreate(
        content_id=f"{context.task}.generated.{generated.content_instance_id}.v2",
        task=context.task, stage=context.stage, step=context.step, action_type=context.action_type,
        prompt=generated.content.question, options=generated.content.options,
        correct_answer=generated.content.expected_answer, explanation=generated.content.explanation,
        misconception="generated_question_incorrect",
        learning_objectives=generated.content.concepts_tested or context.learning_objectives,
        lesson_content=generated.lesson.model_dump(mode="json"), planner_decision=decision,
        generation_metadata={
            "schema_version": "collection_content_v1", "prompt_version": generated.prompt_version,
            "code_version": generated.code_version, "model": generated.model, "dataset": generated.dataset,
            "content_instance_id": generated.content_instance_id,
            "collection_mode": collection_mode(),
            "assignment_policy": (decision or {}).get("assignment_policy", "legacy_unknown"),
            "selection_probability": (decision or {}).get("selection_probability"),
            "curriculum_context": context.reference_prompt,
            "analogy_preference": context.analogy_preference,
            "java_experience": context.java_experience,
        },
    )


def _collection_planner_decision(decision: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Persist assignment metadata, but never WM state/prediction vectors in collection records."""
    if not decision:
        return None
    allowed = {
        "assignment_policy", "selected_index", "selection_probability",
        "action_probabilities", "candidates",
    }
    return {key: decision[key] for key in allowed if key in decision}


def resume_tutor_content(
    learner_id: str,
    task: str,
    stage: str,
    step: str,
    prompt_version: str,
    review: bool = False,
) -> TutorResumeResponse:
    with connect() as connection:
        lesson_row = connection.execute(
            """SELECT payload FROM tutor_stage_lessons
            WHERE learner_id = ? AND task = ? AND stage = ?""",
            (learner_id, task, stage),
        ).fetchone()
        question_row = connection.execute(
            """SELECT payload, action_type, presentation_id, latest_answer, latest_correct, latest_attempt
            FROM tutor_question_instances
            WHERE learner_id = ? AND task = ? AND stage = ? AND step = ? AND active = 1
            ORDER BY created_at DESC LIMIT 1""",
            (learner_id, task, stage, step),
        ).fetchone()
        restored_content = None
        hint_used = False
        if question_row:
            saved = json.loads(question_row["payload"])
            instance_id = saved["content_instance_id"]
            for prefix in dict.fromkeys([task, "sentiment" if task == "sentiment_classification" else task]):
                content_row = connection.execute("SELECT payload FROM content_items WHERE content_id = ?", (f"{prefix}.generated.{instance_id}.v2",)).fetchone()
                if content_row:
                    restored_content = json.loads(content_row["payload"])
                    break
            exposure_rows = connection.execute("SELECT payload FROM behavior_events WHERE learner_id = ?", (learner_id,)).fetchall()
            hint_used = any(
                (event := json.loads(row["payload"])).get("data", {}).get("content_instance_id") == instance_id
                and event.get("data", {}).get("kind") == "hint_opened"
                for row in exposure_rows
            )
    lesson_payload = json.loads(lesson_row["payload"]) if lesson_row else None
    lesson = lesson_payload.get("lesson") if lesson_payload and (review or lesson_payload.get("prompt_version") == prompt_version) else None
    active_question = json.loads(question_row["payload"]) if question_row else None
    if active_question and restored_content:
        active_question["collection_content"] = restored_content
    if active_question and not review and active_question.get("prompt_version") != prompt_version:
        active_question = None
        question_row = None
    question_state = None
    if question_row:
        question_state = TutorQuestionState(
            presentation_id=question_row["presentation_id"],
            answer=question_row["latest_answer"],
            correct=None if question_row["latest_correct"] is None else bool(question_row["latest_correct"]),
            attempt=int(question_row["latest_attempt"] or 1),
            hint_used=hint_used,
        )
    return TutorResumeResponse(
        task=task,
        stage=stage,
        step=step,
        lesson=lesson,
        active_question=active_question,
        action_type=question_row["action_type"] if question_row else None,
        question_state=question_state,
    )


def save_code_execution(
    request: CodeExecutionRequest,
    result: CodeExecutionResult,
    learner_id: str,
) -> None:
    from .collection.config import collection_mode
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        sequence_index = _next_sequence(connection, learner_id, request.session_id)
        connection.execute(
            """INSERT INTO code_executions
            (execution_id, learner_id, session_id, sequence_index, task, stage, step, success, code, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.execution_id, learner_id, request.session_id, sequence_index,
                request.task, request.stage, request.step, int(result.success), request.code,
                json.dumps({
                    "schema_version": "code_execution_v1",
                    "collection_mode": collection_mode(),
                    "request": request.model_dump(mode="json"),
                    "result": result.model_dump(mode="json"),
                }),
            ),
        )


def save_transition(transition: TransitionCreate) -> TransitionRecord:
    payload = transition.model_dump(mode="json")
    with connect() as connection:
        connection.execute(
            "INSERT INTO transitions (transition_id, learner_id, session_id, sequence_index, payload) VALUES (?, ?, ?, ?, ?)",
            (transition.transition_id, transition.learner_id, transition.session_id, transition.sequence_index, json.dumps(payload)),
        )
        row = connection.execute(
            "SELECT payload, created_at FROM transitions WHERE transition_id = ?",
            (transition.transition_id,),
        ).fetchone()
    return TransitionRecord(**json.loads(row["payload"]), created_at=_created_at(row["created_at"]))


def get_transition(transition_id: str) -> Optional[TransitionRecord]:
    with connect() as connection:
        row = connection.execute(
            "SELECT payload, created_at FROM transitions WHERE transition_id = ?",
            (transition_id,),
        ).fetchone()
    if row is None:
        return None
    return _transition_record(row)


def list_transitions(limit: int = 100) -> List[TransitionRecord]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT payload, created_at FROM transitions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_transition_record(row) for row in rows]


def _transition_record(row: Any) -> TransitionRecord:
    payload = json.loads(row["payload"])
    payload.setdefault("schema_version", "2.1")
    payload.setdefault("learner_id", "legacy-anonymous")
    payload.setdefault("session_id", "legacy-session")
    payload.setdefault("sequence_index", 0)
    payload.setdefault("observation", {}).setdefault("response_time_ms", 0)
    payload.setdefault("event_timestamp", row["created_at"])
    payload.setdefault("selection_policy", "legacy_unspecified")
    return TransitionRecord(**payload, created_at=_created_at(row["created_at"]))


def save_content(content: ContentCreate) -> ContentRecord:
    payload = content.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True)
    with connect() as connection:
        existing = connection.execute(
            "SELECT payload, created_at FROM content_items WHERE content_id = ?",
            (content.content_id,),
        ).fetchone()
        if existing is not None:
            if json.dumps(json.loads(existing["payload"]), sort_keys=True) != encoded:
                raise ValueError("content_id already exists with different content")
            return ContentRecord(
                **json.loads(existing["payload"]), created_at=_created_at(existing["created_at"])
            )
        connection.execute(
            "INSERT INTO content_items (content_id, payload) VALUES (?, ?)",
            (content.content_id, encoded),
        )
        row = connection.execute(
            "SELECT payload, created_at FROM content_items WHERE content_id = ?",
            (content.content_id,),
        ).fetchone()
    return ContentRecord(**json.loads(row["payload"]), created_at=_created_at(row["created_at"]))


def get_content(content_id: str) -> Optional[ContentRecord]:
    with connect() as connection:
        row = connection.execute(
            "SELECT payload, created_at FROM content_items WHERE content_id = ?",
            (content_id,),
        ).fetchone()
    if row is None:
        return None
    return ContentRecord(**json.loads(row["payload"]), created_at=_created_at(row["created_at"]))


def list_content(limit: int = 100) -> List[ContentRecord]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT payload, created_at FROM content_items ORDER BY rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        ContentRecord(**json.loads(row["payload"]), created_at=_created_at(row["created_at"]))
        for row in rows
    ]
