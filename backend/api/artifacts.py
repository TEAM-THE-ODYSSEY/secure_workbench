from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

try:
    from backend import artifact_store
except ImportError:
    import artifact_store

router = APIRouter(prefix="/artifacts", tags=["artifacts"])

CONTENT_TYPES: dict[str, str] = {
    "txt": "text/plain; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "csv": "text/csv; charset=utf-8",
}


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: str):
    """Download a generated artifact by artifact_id.

    Never resolves raw filesystem paths directly from user input.
    Lookups are resolved strictly via the server-side artifact lookup table.
    """
    # Reject path traversal or raw paths immediately
    if ".." in artifact_id or "/" in artifact_id or "\\" in artifact_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    # Server-side lookup
    record = artifact_store.get_artifact(artifact_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{artifact_id}' not found",
        )

    file_path = Path(record["file_path"])
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact file for '{artifact_id}' not found on server",
        )

    file_type = record.get("file_type", "").lower()
    content_type = CONTENT_TYPES.get(file_type, "application/octet-stream")
    file_name = record.get("file_name", file_path.name)

    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        filename=file_name,
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
        },
    )
