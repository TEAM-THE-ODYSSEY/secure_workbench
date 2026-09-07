"""
Workspaces & AI Notes REST API Router.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

try:
    from backend.auth_deps import get_current_user
    from backend.schemas.auth import User
except ImportError:
    from auth_deps import get_current_user
    from schemas.auth import User

from workspace.service import workspace_service

router = APIRouter(prefix="/v1/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    title: str
    description: Optional[str] = None


class SaveNoteRequest(BaseModel):
    workspace_id: Optional[str] = None
    title: str
    content: str
    entity_tags: Optional[List[str]] = None
    citations: Optional[List[Dict[str, Any]]] = None


class NoteResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    content: str
    entity_tags: List[str]
    citations: List[Dict[str, Any]]
    created_at: str


@router.get("", response_model=List[Dict[str, Any]])
def list_workspaces(current_user: User = Depends(get_current_user)):
    """List workspaces owned by authenticated user."""
    workspaces = workspace_service.get_user_workspaces(current_user.user_id)
    return [
        {
            "id": w.id,
            "title": w.title,
            "description": w.description,
            "created_at": w.created_at.isoformat() if w.created_at else "",
        }
        for w in workspaces
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_workspace(req: CreateWorkspaceRequest, current_user: User = Depends(get_current_user)):
    """Create a new persistent workspace."""
    ws = workspace_service.create_workspace(current_user.user_id, req.title, req.description)
    return {"id": ws.id, "title": ws.title, "description": ws.description}


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def save_ai_note(req: SaveNoteRequest, current_user: User = Depends(get_current_user)):
    """Save an AI-generated note into a workspace with citation provenance."""
    ws_id = req.workspace_id or "default_workspace"
    note = workspace_service.create_ai_note(
        user_id=current_user.user_id,
        workspace_id=ws_id,
        title=req.title,
        content=req.content,
        entity_tags=req.entity_tags,
        citations=req.citations,
    )
    return NoteResponse(
        id=note.id,
        workspace_id=note.workspace_id,
        title=note.title,
        content=note.content,
        entity_tags=note.entity_tags or [],
        citations=note.citations_json or [],
        created_at=note.created_at.isoformat() if note.created_at else "",
    )


@router.get("/{workspace_id}/notes", response_model=List[NoteResponse])
def get_workspace_notes(workspace_id: str, current_user: User = Depends(get_current_user)):
    """Retrieve saved AI notes for a specific workspace."""
    notes = workspace_service.get_workspace_notes(current_user.user_id, workspace_id)
    return [
        NoteResponse(
            id=n.id,
            workspace_id=n.workspace_id,
            title=n.title,
            content=n.content,
            entity_tags=n.entity_tags or [],
            citations=n.citations_json or [],
            created_at=n.created_at.isoformat() if n.created_at else "",
        )
        for n in notes
    ]
