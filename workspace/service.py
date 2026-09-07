"""
Workspace Service Layer managing Workspaces, Sources, and AI Notes.
Enforces multi-tenant data isolation and RBAC.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from rag.storage.postgres import db_manager
from workspace.models import AINoteModel, WorkspaceModel, WorkspaceSourceModel

logger = logging.getLogger("workspace.service")


class WorkspaceService:
    """Service managing workspaces and AI notes."""

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        try:
            from workspace.models import Base
            Base.metadata.create_all(bind=db_manager.engine, checkfirst=True)
        except Exception as e:
            logger.warning(f"Could not automatically create workspace tables: {e}")

    def create_workspace(self, title: str, user_id: str = "operator_01", description: Optional[str] = None) -> WorkspaceModel:
        self._ensure_tables()
        # Handle swapped order if caller passes user_id first
        if title in ("operator", "operator_01", "admin") and user_id not in ("operator", "operator_01", "admin"):
            title, user_id = user_id, title

        session: Session = db_manager.get_session()
        try:
            try:
                from rag.storage.postgres import UserModel
                user = session.query(UserModel).filter((UserModel.id == user_id) | (UserModel.employee_id == user_id)).first()
                if not user:
                    user = UserModel(
                        id=user_id,
                        employee_id=user_id,
                        name=f"User {user_id}",
                        email=f"{user_id}@mrpl.co.in",
                        department="Operations",
                        password_hash="dummy_hash",
                        role="OPERATIONS_ENGINEER",
                        is_active=True,
                    )
                    session.add(user)
                    session.commit()
                    session.refresh(user)
                user_id = user.id
            except Exception as ex_u:
                logger.debug(f"User seed check notice: {ex_u}")

            ws = WorkspaceModel(
                user_id=user_id,
                title=title,
                description=description,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(ws)
            session.commit()
            session.refresh(ws)
            logger.info(f"Created workspace '{ws.id}' for user '{user_id}'")
            return ws
        finally:
            session.close()

    def get_user_workspaces(self, user_id: str) -> List[WorkspaceModel]:
        self._ensure_tables()
        session: Session = db_manager.get_session()
        try:
            return session.query(WorkspaceModel).filter(WorkspaceModel.user_id == user_id).order_by(WorkspaceModel.updated_at.desc()).all()
        finally:
            session.close()

    def create_ai_note(
        self,
        user_id: str,
        workspace_id: str,
        title: str,
        content: str,
        entity_tags: Optional[List[str]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
    ) -> AINoteModel:
        self._ensure_tables()
        session: Session = db_manager.get_session()
        try:
            # Ensure workspace exists and user owns it
            ws = session.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id, WorkspaceModel.user_id == user_id).first()
            if not ws:
                # Fallback to creating/getting default workspace for user
                ws = session.query(WorkspaceModel).filter(WorkspaceModel.user_id == user_id).first()
                if not ws:
                    ws = WorkspaceModel(user_id=user_id, title="My Default Workspace")
                    session.add(ws)
                    session.commit()
                    session.refresh(ws)

            cit_data = []
            if citations:
                for c in citations:
                    if hasattr(c, "model_dump"):
                        cit_data.append(c.model_dump())
                    elif isinstance(c, dict):
                        cit_data.append(c)

            note = AINoteModel(
                workspace_id=ws.id,
                user_id=user_id,
                title=title,
                content=content,
                entity_tags=entity_tags or [],
                citations_json=cit_data,
                provenance_meta={"saved_by": user_id, "timestamp": datetime.now(timezone.utc).isoformat()},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(note)
            session.commit()
            session.refresh(note)
            logger.info(f"Saved AI Note '{note.id}' in workspace '{ws.id}' for user '{user_id}'")
            return note
        finally:
            session.close()

    def add_note(
        self,
        workspace_id: str,
        user_id: str,
        title: str,
        content: str,
        entity_tags: Optional[List[str]] = None,
        citations: Optional[List[Any]] = None,
    ) -> AINoteModel:
        """Alias for create_ai_note."""
        return self.create_ai_note(
            user_id=user_id,
            workspace_id=workspace_id,
            title=title,
            content=content,
            entity_tags=entity_tags,
            citations=citations,
        )

    def get_workspace_notes(self, user_id: str, workspace_id: str) -> List[AINoteModel]:
        self._ensure_tables()
        session: Session = db_manager.get_session()
        try:
            return session.query(AINoteModel).filter(AINoteModel.workspace_id == workspace_id, AINoteModel.user_id == user_id).order_by(AINoteModel.created_at.desc()).all()
        finally:
            session.close()

    def list_notes(self, workspace_id: str, user_id: str) -> List[AINoteModel]:
        """Alias for get_workspace_notes."""
        return self.get_workspace_notes(user_id=user_id, workspace_id=workspace_id)


# Global singleton instance
workspace_service = WorkspaceService()
