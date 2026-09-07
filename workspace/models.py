"""
SQLAlchemy ORM Models for Native Persistent Workspace / Notebook Layer.
Provides per-user workspace isolation, workspace sources, and AI notes with citation provenance.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import declarative_base, relationship

try:
    from rag.storage.postgres import Base
except ImportError:
    Base = declarative_base()


class WorkspaceModel(Base):
    """Persistent Workspace / Notebook grouping conversations, sources, notes, and reports."""
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True, default=lambda: f"ws_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_private = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    notes = relationship("AINoteModel", back_populates="workspace", cascade="all, delete-orphan")
    sources = relationship("WorkspaceSourceModel", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceSourceModel(Base):
    """Source documents associated with a workspace."""
    __tablename__ = "workspace_sources"

    id = Column(String(64), primary_key=True, default=lambda: f"wss_{uuid.uuid4().hex[:12]}")
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(64), nullable=False)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), default="application/pdf")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace = relationship("WorkspaceModel", back_populates="sources")


class AINoteModel(Base):
    """Persistent AI-generated Note saved into a Workspace with citation provenance."""
    __tablename__ = "ai_notes"

    id = Column(String(64), primary_key=True, default=lambda: f"note_{uuid.uuid4().hex[:12]}")
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    entity_tags = Column(JSON, default=list)  # e.g. ["EQ-P101A"]
    citations_json = Column(JSON, default=list)  # Document IDs & versions
    provenance_meta = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace = relationship("WorkspaceModel", back_populates="notes")
