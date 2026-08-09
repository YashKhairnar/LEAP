import json
import os
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
from .models import (
    AuthResponse,
    BehaviorEventCreate,
    BehaviorEventRecord,
    ContentCreate,
    ContentRecord,
    InteractionCreate,
    TransitionCreate,
    TransitionRecord,
    UserRecord,
)


DEFAULT_DATABASE = Path(__file__).resolve().parent.parent / "data" / "leap.db"
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
            email TEXT NOT NULL UNIQUE,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
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
        if not connection.postgres:
            transition_columns = {row["name"] for row in connection.execute("PRAGMA table_info(transitions)").fetchall()}
            for column, column_type in (("learner_id", "TEXT"), ("session_id", "TEXT"), ("sequence_index", "INTEGER")):
                if column not in transition_columns:
                    connection.execute(f"ALTER TABLE transitions ADD COLUMN {column} {column_type}")
            user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
            if "consent_version" not in user_columns:
                connection.execute("ALTER TABLE users ADD COLUMN consent_version TEXT NOT NULL DEFAULT 'legacy'")
            if "consented_at" not in user_columns:
                connection.execute("ALTER TABLE users ADD COLUMN consented_at TIMESTAMP")
            auth_columns = {row["name"] for row in connection.execute("PRAGMA table_info(auth_sessions)").fetchall()}
            if "expires_at" not in auth_columns:
                connection.execute("ALTER TABLE auth_sessions ADD COLUMN expires_at TIMESTAMP")


def _created_at(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _user_record(row: Any) -> UserRecord:
    return UserRecord(
        user_id=row["user_id"], email=row["email"], name=row["name"],
        java_experience=row["java_experience"]
    )


def create_user(user_id: str, email: str, password: str, name: str, java_experience: str, consent_version: str) -> AuthResponse:
    salt, password_hash = hash_password(password)
    token = new_access_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    with connect() as connection:
        connection.execute(
            "INSERT INTO users (user_id, email, password_salt, password_hash, name, java_experience, consent_version) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, email, salt, password_hash, name, java_experience, consent_version),
        )
        connection.execute(
            "INSERT INTO auth_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_digest(token), user_id, expires_at),
        )
        row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return AuthResponse(access_token=token, user=_user_record(row))


def authenticate_user(email: str, password: str) -> Optional[AuthResponse]:
    with connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
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
        encoded_content = json.dumps(content_payload, sort_keys=True)
        existing = connection.execute(
            "SELECT payload FROM content_items WHERE content_id = ?", (interaction.content.content_id,)
        ).fetchone()
        if existing is not None and json.dumps(json.loads(existing["payload"]), sort_keys=True) != encoded_content:
            raise ValueError("content_id already exists with different content")
        if existing is None:
            connection.execute(
                "INSERT INTO content_items (content_id, payload) VALUES (?, ?)",
                (interaction.content.content_id, encoded_content),
            )
        if interaction.instructional_action.content_id != interaction.content.content_id:
            raise ValueError("instructional action and content IDs must match")
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
            "selection_policy": interaction.selection_policy,
        }
        connection.execute(
            "INSERT INTO transitions (transition_id, learner_id, session_id, sequence_index, payload) VALUES (?, ?, ?, ?, ?)",
            (interaction.transition_id, learner_id, interaction.session_id, sequence_index, json.dumps(payload)),
        )
        row = connection.execute(
            "SELECT payload, created_at FROM transitions WHERE transition_id = ?", (interaction.transition_id,)
        ).fetchone()
    return TransitionRecord(**json.loads(row["payload"]), created_at=_created_at(row["created_at"]))


def save_behavior_event(event: BehaviorEventCreate, learner_id: str) -> BehaviorEventRecord:
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        sequence_index = _next_sequence(connection, learner_id, event.session_id)
        payload = event.model_dump(mode="json")
        connection.execute(
            "INSERT INTO behavior_events (event_id, learner_id, session_id, sequence_index, payload) VALUES (?, ?, ?, ?, ?)",
            (event.event_id, learner_id, event.session_id, sequence_index, json.dumps(payload)),
        )
        row = connection.execute(
            "SELECT created_at FROM behavior_events WHERE event_id = ?", (event.event_id,)
        ).fetchone()
    return BehaviorEventRecord(**payload, learner_id=learner_id, sequence_index=sequence_index, created_at=_created_at(row["created_at"]))


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
