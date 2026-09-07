from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import psutil

try:
    from backend.schemas.network import NetworkConnection, NetworkStatus
except ImportError:
    from schemas.network import NetworkConnection, NetworkStatus

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}

KNOWN_LOCAL_SERVICES: dict[int, str] = {
    11434: "Ollama (LLM/Vision/Embeddings)",
    8000: "Backend API",
}

DB_PATH = Path(
    os.getenv(
        "TASK_STORE_DB_PATH",
        Path(__file__).resolve().parent / "workspace" / "tasks.db",
    )
)

_memory_blocked_attempts: list[dict] = []


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS blocked_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reason TEXT NOT NULL,
            task_id TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    return conn


def record_blocked_attempt(reason: str, task_id: str) -> None:
    """Record an unauthorized or refused external network access attempt."""
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "reason": reason,
        "task_id": task_id,
        "timestamp": now_iso,
    }
    _memory_blocked_attempts.append(record)

    try:
        conn = _get_connection()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO blocked_attempts (reason, task_id, timestamp) VALUES (?, ?, ?)",
                    (reason, task_id, now_iso),
                )
        finally:
            conn.close()
    except Exception:
        pass


def get_blocked_attempts() -> list[dict]:
    """Retrieve all blocked attempts from SQLite store or memory."""
    try:
        conn = _get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reason, task_id, timestamp FROM blocked_attempts ORDER BY id ASC"
            )
            rows = cursor.fetchall()
            if rows:
                return [
                    {"reason": r[0], "task_id": r[1], "timestamp": r[2]}
                    for r in rows
                ]
        finally:
            conn.close()
    except Exception:
        pass

    return list(_memory_blocked_attempts)


def snapshot() -> NetworkStatus:
    """Capture current network connections and classify local vs external."""
    local_conns: list[NetworkConnection] = []
    ext_conns: list[NetworkConnection] = []

    current_pid = os.getpid()
    relevant_pids = {current_pid}
    try:
        proc = psutil.Process(current_pid)
        for child in proc.children(recursive=True):
            relevant_pids.add(child.pid)
    except Exception:
        pass

    try:
        connections = psutil.net_connections(kind="inet")
    except Exception:
        connections = []

    seen = set()
    monitor_all = os.getenv("WORKBENCH_MONITOR_ALL") == "1"

    for c in connections:
        is_workbench = False
        if c.pid in relevant_pids:
            is_workbench = True
        elif c.laddr and c.laddr.port in KNOWN_LOCAL_SERVICES:
            is_workbench = True
        elif c.raddr and c.raddr.port in KNOWN_LOCAL_SERVICES:
            is_workbench = True

        if not monitor_all and not is_workbench:
            continue

        if c.raddr:
            r_ip = c.raddr.ip
            r_port = c.raddr.port
            remote_str = f"{r_ip}:{r_port}"
            is_local = (
                r_ip in LOCAL_HOSTS
                or r_ip.startswith("127.")
                or r_ip == "::1"
            )
            service_name = (
                KNOWN_LOCAL_SERVICES.get(r_port)
                or (KNOWN_LOCAL_SERVICES.get(c.laddr.port) if c.laddr else None)
            )
            if not service_name:
                service_name = "Local Service" if is_local else "External / Cloud"

            conn_obj = NetworkConnection(
                remote=remote_str,
                service=service_name,
                status=c.status,
            )
        else:
            l_ip = c.laddr.ip if c.laddr else "127.0.0.1"
            l_port = c.laddr.port if c.laddr else 0
            is_local = (
                l_ip in LOCAL_HOSTS
                or l_ip.startswith("127.")
                or l_ip in ("0.0.0.0", "::")
            )
            remote_str = f"{l_ip}:{l_port}"
            service_name = KNOWN_LOCAL_SERVICES.get(l_port, f"Port {l_port}")
            conn_obj = NetworkConnection(
                remote=remote_str,
                service=service_name,
                status=c.status,
            )

        key = (conn_obj.remote, conn_obj.service, conn_obj.status)
        if key in seen:
            continue
        seen.add(key)

        if is_local:
            local_conns.append(conn_obj)
        else:
            ext_conns.append(conn_obj)

    sovereign = len(ext_conns) == 0

    return NetworkStatus(
        local_connections=local_conns,
        external_connections=ext_conns,
        blocked_attempts=get_blocked_attempts(),
        sovereign=sovereign,
    )
