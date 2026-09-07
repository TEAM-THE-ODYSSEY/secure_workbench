from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

try:
    from backend.schemas.shared_schemas import ModelInfo
except ImportError:
    from schemas.shared_schemas import ModelInfo

# Default to workspace/tasks.db matching task_store.py
DB_PATH = Path(
    os.getenv(
        "TASK_STORE_DB_PATH",
        Path(__file__).resolve().parent / "workspace" / "tasks.db",
    )
)

JSON_PATH = Path(
    os.getenv(
        "MODEL_REGISTRY_JSON_PATH",
        Path(__file__).resolve().parent / "workspace" / "model_registry.json",
    )
)

DEFAULT_MODELS: list[ModelInfo] = [
    ModelInfo(
        model_id="general_model",
        model_name="llama3.1:8b",
        model_type="general",
        capabilities=["chat"],
        context_length=8192,
        quantization="Q4_K_M",
        memory_requirement="8GB",
        supported_tasks=["SIMPLE"],
        ollama_tag="llama3.1:8b",
        is_default_for_tasks=["SIMPLE"],
    ),
    ModelInfo(
        model_id="reasoning_model",
        model_name="llama3.1:8b-instruct",
        model_type="reasoning",
        capabilities=["multi-step reasoning", "tool use"],
        context_length=8192,
        quantization="Q4_K_M",
        memory_requirement="8GB",
        supported_tasks=["REASONING", "DOCUMENT"],
        ollama_tag="llama3.1:8b-instruct",
        is_default_for_tasks=["REASONING", "DOCUMENT"],
    ),
    ModelInfo(
        model_id="coding_model",
        model_name="qwen2.5-coder:7b",
        model_type="coding",
        capabilities=["code generation", "debugging"],
        context_length=32768,
        quantization="Q4_K_M",
        memory_requirement="8GB",
        supported_tasks=["CODING"],
        ollama_tag="qwen2.5-coder:7b",
        is_default_for_tasks=["CODING"],
    ),
    ModelInfo(
        model_id="vision_model",
        model_name="llava:7b",
        model_type="vision",
        capabilities=["image understanding"],
        context_length=4096,
        quantization="Q4_K_M",
        memory_requirement="8GB",
        supported_tasks=["MULTIMODAL"],
        ollama_tag="llava:7b",
        is_default_for_tasks=["MULTIMODAL"],
    ),
    ModelInfo(
        model_id="embedding_model",
        model_name="nomic-embed-text",
        model_type="embedding",
        capabilities=["text embedding"],
        context_length=2048,
        quantization="F16",
        memory_requirement="2GB",
        supported_tasks=["REASONING", "DOCUMENT"],
        ollama_tag="nomic-embed-text",
        is_default_for_tasks=[],
    ),
]


def _sync_json(models: list[ModelInfo]) -> None:
    """Sync model registry to workspace/model_registry.json."""
    try:
        JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"models": [m.model_dump() for m in models]}
        JSON_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS models (
            model_id TEXT PRIMARY KEY,
            model_json TEXT NOT NULL
        )
        """
    )
    # Check if empty, seed default models
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM models")
    count = cursor.fetchone()[0]
    if count == 0:
        for model in DEFAULT_MODELS:
            conn.execute(
                "INSERT INTO models (model_id, model_json) VALUES (?, ?)",
                (model.model_id, model.model_dump_json()),
            )
        conn.commit()
        _sync_json(DEFAULT_MODELS)
    return conn


def get_all_models() -> list[ModelInfo]:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT model_json FROM models ORDER BY rowid ASC")
        rows = cursor.fetchall()
        models = [ModelInfo.model_validate_json(row[0]) for row in rows]
        _sync_json(models)
        return models
    finally:
        conn.close()


def get_model(model_id: str) -> Optional[ModelInfo]:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT model_json FROM models WHERE model_id = ?", (model_id,))
        row = cursor.fetchone()
        if row:
            return ModelInfo.model_validate_json(row[0])
        return None
    finally:
        conn.close()


def model_exists(model_id: str) -> bool:
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM models WHERE model_id = ?", (model_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def save_model(model: ModelInfo) -> None:
    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO models (model_id, model_json)
                VALUES (?, ?)
                ON CONFLICT(model_id) DO UPDATE SET
                    model_json = excluded.model_json
                """,
                (model.model_id, model.model_dump_json()),
            )
        # Update JSON file
        all_models = get_all_models()
        _sync_json(all_models)
    finally:
        conn.close()
