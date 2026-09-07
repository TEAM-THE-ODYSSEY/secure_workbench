from __future__ import annotations
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional
from passlib.context import CryptContext

try:
    from backend.schemas.auth import User
except ImportError:
    from schemas.auth import User

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

DB_PATH = Path(
    os.getenv(
        "TASK_STORE_DB_PATH",
        Path(__file__).resolve().parent / "workspace" / "tasks.db",
    )
)


class UserAlreadyExistsError(Exception):
    pass


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
        """
    )
    # Check if 'role' column exists in case table was created previously
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "role" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        conn.commit()

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"
    )
    return conn


async def has_admin_user() -> bool:
    """Return True if at least one user with role='admin' exists."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1")
        return cursor.fetchone() is not None
    finally:
        conn.close()


async def count_admin_users() -> int:
    """Return count of users with role='admin'."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        row = cursor.fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


async def create_user(
    username: str,
    password: str,
    role: Literal["admin", "user"] = "user",
) -> User:
    """Create a new user with hashed password and role.

    Role defaults to 'user' and cannot be set via public registration bodies.
    Plaintext password is never stored or logged.
    """
    conn = _get_connection()
    try:
        user_id = str(uuid.uuid4())
        password_hash = pwd_context.hash(password)
        created_at = datetime.now(timezone.utc).isoformat()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO users (user_id, username, password_hash, role, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, username, password_hash, role, created_at),
                )
        except sqlite3.IntegrityError:
            raise UserAlreadyExistsError(f"Username '{username}' is already taken")
        return User(user_id=user_id, username=username, role=role, created_at=created_at)
    finally:
        conn.close()


async def get_user_by_username(username: str) -> Optional[User]:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username, role, created_at FROM users WHERE username = ?",
            (username,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return User(user_id=row[0], username=row[1], role=row[2], created_at=row[3])
    finally:
        conn.close()


async def get_user_by_id(user_id: str) -> Optional[User]:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username, role, created_at FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return User(user_id=row[0], username=row[1], role=row[2], created_at=row[3])
    finally:
        conn.close()


async def verify_password(username: str, password: str) -> Optional[User]:
    """Verify credentials without logging or exposing password.

    Returns User with role if valid, None if invalid or user does not exist.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username, password_hash, role, created_at FROM users WHERE username = ?",
            (username,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        user_id, uname, pwd_hash, role, created_at = row
        if not pwd_context.verify(password, pwd_hash):
            return None
        return User(user_id=user_id, username=uname, role=role, created_at=created_at)
    finally:
        conn.close()
