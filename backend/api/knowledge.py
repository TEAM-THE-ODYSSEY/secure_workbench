from __future__ import annotations
import json
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

try:
    from backend.schemas.knowledge import IngestResponse, KnowledgeDocument
    from backend.schemas.auth import User
    from backend.auth_deps import get_current_admin, get_current_user
except ImportError:
    from schemas.knowledge import IngestResponse, KnowledgeDocument
    from schemas.auth import User
    from auth_deps import get_current_admin, get_current_user

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

KB_DIR = Path(
    os.getenv(
        "KNOWLEDGE_BASE_DIR",
        Path(__file__).resolve().parent.parent / "workspace" / "knowledge_base",
    )
)
INDEX_PATH = KB_DIR / "index.json"


def _load_index() -> list[dict]:
    if not INDEX_PATH.exists():
        return []
    try:
        content = INDEX_PATH.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _save_index(records: list[dict]) -> None:
    KB_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    _admin: User = Depends(get_current_admin),
):
    """Ingest a single document into the local knowledge base (admin only)."""
    filename = file.filename or ""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename cannot be empty",
        )

    # Reject path traversal or absolute paths
    if ".." in filename or os.path.isabs(filename) or filename.startswith("/") or filename.startswith("\\"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid filename '{filename}': path traversal or absolute paths are not permitted",
        )

    content = await file.read()
    # Stub plausible chunks count based on file size (~500 bytes per chunk)
    chunks_indexed = max(1, len(content) // 500)
    document_id = str(uuid.uuid4())

    KB_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = KB_DIR / filename
    dest_path.write_bytes(content)

    records = _load_index()
    record = {
        "document_id": document_id,
        "document_name": filename,
        "chunks_indexed": chunks_indexed,
    }
    records.append(record)
    _save_index(records)

    return IngestResponse(document_id=document_id, chunks_indexed=chunks_indexed)


@router.get("/documents", response_model=list[KnowledgeDocument])
async def list_documents(
    _user: User = Depends(get_current_user),
):
    """List all ingested documents in the knowledge base (authenticated users)."""
    records = _load_index()
    return [KnowledgeDocument(**r) for r in records]
