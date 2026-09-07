from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder

try:
    from backend.schemas.chat_history import ChatSession, ChatMessage, RenameSessionRequest
    from backend.schemas.auth import User
    from backend.schemas.shared_schemas import TaskFinalResponse, TaskState
    from backend.auth_deps import get_current_user
    from backend import chat_history_store, task_store
except ImportError:
    from schemas.chat_history import ChatSession, ChatMessage, RenameSessionRequest
    from schemas.auth import User
    from schemas.shared_schemas import TaskFinalResponse, TaskState
    from auth_deps import get_current_user
    import chat_history_store
    import task_store

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[ChatSession])
async def list_user_sessions(
    current_user: User = Depends(get_current_user),
):
    """List authenticated user's chat sessions, most recently updated first."""
    return await chat_history_store.list_sessions(current_user.user_id)


@router.get("/{session_id}/messages", response_model=list[ChatMessage])
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieve all messages in a session, embedding task results for assistant messages."""
    session = await chat_history_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this session is forbidden",
        )

    raw_messages = await chat_history_store.list_messages(session_id)
    enriched_messages: list[ChatMessage] = []

    for msg in raw_messages:
        result = None
        task_id = msg.get("task_id")
        if msg.get("role") == "assistant" and task_id:
            task_state = task_store.load(task_id)
            if task_state is not None:
                if task_state.status in ("COMPLETED", "FAILED"):
                    result = jsonable_encoder(TaskFinalResponse.from_task_state(task_state))
                else:
                    result = jsonable_encoder(task_state)

        enriched_messages.append(
            ChatMessage(
                message_id=msg["message_id"],
                session_id=msg["session_id"],
                role=msg["role"],
                content=msg.get("content"),
                task_id=task_id,
                created_at=msg["created_at"],
                result=result,
            )
        )

    return enriched_messages


@router.patch("/{session_id}", response_model=ChatSession)
async def rename_session(
    session_id: str,
    body: RenameSessionRequest,
    current_user: User = Depends(get_current_user),
):
    """Rename a chat session owned by the authenticated user."""
    session = await chat_history_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this session is forbidden",
        )

    await chat_history_store.rename_session(session_id, body.title)
    updated = await chat_history_store.get_session(session_id)
    return updated


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session and cascade to its messages."""
    session = await chat_history_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this session is forbidden",
        )

    await chat_history_store.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}
