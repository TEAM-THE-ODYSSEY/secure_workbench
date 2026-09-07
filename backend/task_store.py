from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import Optional

try:
    from backend.schemas.shared_schemas import TaskState
except ImportError:
    from schemas.shared_schemas import TaskState

# Default to workspace/tasks.db located in the backend package directory
DB_PATH = Path(
    os.getenv(
        "TASK_STORE_DB_PATH",
        Path(__file__).resolve().parent / "workspace" / "tasks.db",
    )
)


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            state_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"
    )
    return conn


def save(state: TaskState) -> None:
    conn = _get_connection()
    try:
        payload = state.model_dump_json()
        with conn:
            conn.execute(
                """
                INSERT INTO tasks (task_id, status, state_json)
                VALUES (?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status = excluded.status,
                    state_json = excluded.state_json
                """,
                (state.task_id, state.status, payload),
            )
    finally:
        conn.close()


def load(task_id: str) -> Optional[TaskState]:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT state_json FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return TaskState.model_validate_json(row[0])
    finally:
        conn.close()


def exists(task_id: str) -> bool:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()
