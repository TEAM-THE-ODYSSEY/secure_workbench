from __future__ import annotations
import os
import uuid
from pathlib import Path
from typing import Optional, Union
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

try:
    from backend import chat_history_store, engine_bridge
    from backend.auth_deps import get_current_user
    from backend.schemas.auth import User
    from backend.schemas.shared_schemas import (
        TaskCreatedResponse,
        TaskFinalResponse,
        TaskState,
    )
except ImportError:
    import chat_history_store
    import engine_bridge
    from auth_deps import get_current_user
    from schemas.auth import User
    from schemas.shared_schemas import (
        TaskCreatedResponse,
        TaskFinalResponse,
        TaskState,
    )

router = APIRouter(tags=["chat"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "csv", "txt", "png", "jpg", "jpeg"}
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "workspace" / "uploads"


@router.post(
    "/chat",
    response_model=TaskCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_chat_task(
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    files: Optional[list[UploadFile]] = File(None),
    current_user: User = Depends(get_current_user),
):
    # 1. Validate all files before writing anything to disk
    valid_files = [f for f in (files or []) if f.filename]
    for upload in valid_files:
        filename = upload.filename or ""

        # Reject path traversal or absolute paths
        if ".." in filename or os.path.isabs(filename) or filename.startswith("/") or filename.startswith("\\"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid filename '{filename}': path traversal or absolute paths are not permitted",
            )

        # Reject missing or disallowed extension
        if "." not in filename:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{filename}' has no extension. Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}",
            )
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File extension '.{ext}' is not permitted. Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}",
            )

    # 2. Resolve or create chat session
    effective_title = message[:40].strip() or "New Chat"
    if not session_id:
        new_session = await chat_history_store.create_session(
            user_id=current_user.user_id,
            title=effective_title,
        )
        effective_session_id = new_session.session_id
    else:
        existing_session = await chat_history_store.get_session(session_id)
        if existing_session is None:
            new_session = await chat_history_store.create_session(
                user_id=current_user.user_id,
                title=effective_title,
                session_id=session_id,
            )
            effective_session_id = new_session.session_id
        else:
            if existing_session.user_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access to this session is forbidden",
                )
            effective_session_id = existing_session.session_id

    # 3. Record user message
    await chat_history_store.add_message(
        session_id=effective_session_id,
        role="user",
        content=message,
        task_id=None,
    )

    # 4. Save valid files to workspace/uploads/{session_id}/{filename}
    session_dir = UPLOADS_DIR / effective_session_id
    saved_file_paths: list[str] = []

    if valid_files:
        session_dir.mkdir(parents=True, exist_ok=True)
        for upload in valid_files:
            file_dest = session_dir / (upload.filename or "")
            content = await upload.read()
            file_dest.write_bytes(content)
            saved_file_paths.append(str(file_dest.resolve()))

    # 5. Call engine bridge with absolute file paths
    task_id = engine_bridge.start_task(message, saved_file_paths)

    # 6. Record assistant message placeholder linked to task_id
    await chat_history_store.add_message(
        session_id=effective_session_id,
        role="assistant",
        content=None,
        task_id=task_id,
    )

    # 7. Update session updated_at
    await chat_history_store.touch_session(effective_session_id)

    # 8. Return 202 Accepted with TaskCreatedResponse
    return TaskCreatedResponse(
        task_id=task_id,
        session_id=effective_session_id,
        status="CREATED",
    )


@router.get(
    "/tasks/{task_id}",
    response_model=Union[TaskFinalResponse, TaskState],
)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    state = engine_bridge.get_task_state(task_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if state.status in ("COMPLETED", "FAILED"):
        return TaskFinalResponse.from_task_state(state)

    return state
