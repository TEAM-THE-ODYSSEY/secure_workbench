from __future__ import annotations
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from backend.schemas.chat_history import ChatSession
except ImportError:
    from schemas.chat_history import ChatSession

DB_PATH = Path(
    os.getenv(
        "CHAT_STORE_DB_PATH",
        Path(__file__).resolve().parent / "workspace" / "chat_history.db",
    )
)


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            task_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        )
        """
    )
    return conn


async def create_session(
    user_id: str,
    title: str,
    session_id: Optional[str] = None,
) -> ChatSession:
    sid = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sid, user_id, title, now, now),
            )
        return ChatSession(
            session_id=sid,
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
    finally:
        conn.close()


async def list_sessions(user_id: str) -> list[ChatSession]:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, user_id, title, created_at, updated_at
            FROM sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [
            ChatSession(
                session_id=r[0],
                user_id=r[1],
                title=r[2],
                created_at=r[3],
                updated_at=r[4],
            )
            for r in rows
        ]
    finally:
        conn.close()


async def get_session(session_id: str) -> Optional[ChatSession]:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, user_id, title, created_at, updated_at
            FROM sessions
            WHERE session_id = ?
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        if row:
            return ChatSession(
                session_id=row[0],
                user_id=row[1],
                title=row[2],
                created_at=row[3],
                updated_at=row[4],
            )
        return None
    finally:
        conn.close()


async def rename_session(session_id: str, title: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE sessions
                SET title = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (title, now, session_id),
            )
    finally:
        conn.close()


async def delete_session(session_id: str) -> None:
    conn = _get_connection()
    try:
        with conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    finally:
        conn.close()


async def add_message(
    session_id: str,
    role: str,
    content: Optional[str],
    task_id: Optional[str],
) -> None:
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO messages (message_id, session_id, role, content, task_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (msg_id, session_id, role, content, task_id, now),
            )
    finally:
        conn.close()


async def list_messages(session_id: str) -> list[dict]:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT message_id, session_id, role, content, task_id, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY rowid ASC
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "message_id": r[0],
                "session_id": r[1],
                "role": r[2],
                "content": r[3],
                "task_id": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]
    finally:
        conn.close()


async def touch_session(session_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
    finally:
        conn.close()
