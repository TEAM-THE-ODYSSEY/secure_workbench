"""
PostgreSQL database models, connection management, and SQLAlchemy ORM schemas
for the MRPL Air-Gapped Knowledge Platform.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
import logging
from typing import Generator, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    text,
    create_engine,
)

from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

from rag.config import config

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================
# ENUMS
# ============================================================

class SourceType(str, PyEnum):
    ADMIN_UPLOAD = "ADMIN_UPLOAD"
    FILE_SYSTEM = "FILE_SYSTEM"
    REST_API = "REST_API"
    SQL_DATABASE = "SQL_DATABASE"
    EVENT_SOURCE = "EVENT_SOURCE"


class TrustLevel(str, PyEnum):
    TRUSTED = "TRUSTED"
    VERIFIED = "VERIFIED"
    UNTRUSTED = "UNTRUSTED"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"


class DocumentStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"


class JobStatus(str, PyEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXTRACTING = "EXTRACTING"
    SECURITY_CHECK = "SECURITY_CHECK"
    PROCESSING = "PROCESSING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


class RiskLevel(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingType(str, PyEnum):
    MALWARE = "MALWARE"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    CONTRADICTION = "CONTRADICTION"
    INTEGRITY = "INTEGRITY"
    DUPLICATE = "DUPLICATE"
    SOURCE_TRUST = "SOURCE_TRUST"


class FindingSeverity(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ============================================================
# ORM MODELS
# ============================================================

class SourceModel(Base):
    """Represents a data ingestion source with trust classification."""
    __tablename__ = "sources"

    source_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(32), nullable=False, default=SourceType.ADMIN_UPLOAD.value)
    trust_level = Column(String(32), nullable=False, default=TrustLevel.UNTRUSTED.value, index=True)
    config_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    documents = relationship("DocumentModel", back_populates="source", cascade="all, delete-orphan")


class DocumentModel(Base):
    """SQLAlchemy model for ingested documents with trust and provenance tracking."""
    __tablename__ = "documents"

    id = Column(String(255), primary_key=True)
    source_id = Column(String(255), ForeignKey("sources.source_id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    extension = Column(String(32), nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    document_type = Column(String(64), index=True)
    department = Column(String(128), index=True)
    plant = Column(String(128), index=True)
    unit = Column(String(128), index=True)
    equipment_id = Column(String(128), index=True)
    version = Column(String(64), default="1.0")
    status = Column(String(32), nullable=False, default=DocumentStatus.PENDING.value, index=True)
    trust_level = Column(String(32), nullable=False, default=TrustLevel.UNTRUSTED.value, index=True)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(16), default=RiskLevel.LOW.value)
    storage_uri = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(255), nullable=True)

    source = relationship("SourceModel", back_populates="documents")

    @property
    def title(self) -> str:
        return self.filename

    @title.setter
    def title(self, value: str):
        self.filename = value

    versions = relationship("DocumentVersionModel", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("ChunkModel", back_populates="document", cascade="all, delete-orphan")
    security_findings = relationship("SecurityFindingModel", back_populates="document", cascade="all, delete-orphan")


class DocumentVersionModel(Base):
    """Document version control for revision tracking."""
    __tablename__ = "document_versions"

    version_id = Column(String(255), primary_key=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_code = Column(String(64), nullable=False)
    checksum = Column(String(64), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    change_summary = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document = relationship("DocumentModel", back_populates="versions")


class ChunkModel(Base):
    """Document chunks with text, metadata, and vector embeddings."""
    __tablename__ = "chunks"

    chunk_id = Column(String(255), primary_key=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(String(255), index=True)
    parent_chunk_id = Column(String(255), index=True, nullable=True)
    chunk_type = Column(String(32), default="child")  # child, parent, standalone
    content = Column(Text, nullable=False)
    page_number = Column(Integer, default=1)
    section_title = Column(String(255), default="General")
    chunk_index = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    trust_level = Column(String(32), default=TrustLevel.UNTRUSTED.value, index=True)
    metadata_json = Column(JSON, default=dict)
    # embedding stored as JSON array; native pgvector column added via migration
    embedding_json = Column(JSON, nullable=True)

    document = relationship("DocumentModel", back_populates="chunks")
    chunk_entities = relationship("ChunkEntityModel", back_populates="chunk", cascade="all, delete-orphan")

    # GIN index for PostgreSQL Full-Text Search (created via migration)
    __table_args__ = (
        Index("ix_chunks_content_fts", "content", postgresql_using="gin",
              postgresql_ops={"content": "gin_trgm_ops"}),
    )


class EntityModel(Base):
    """Canonical entities (equipment, units, departments) for knowledge organization."""
    __tablename__ = "entities"

    entity_id = Column(String(255), primary_key=True)
    canonical_name = Column(String(255), nullable=False, unique=True, index=True)
    entity_type = Column(String(64), nullable=False, index=True)  # EQUIPMENT, UNIT, DEPARTMENT, etc.
    aliases_json = Column(JSON, default=list)  # List of known aliases
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    chunk_links = relationship("ChunkEntityModel", back_populates="entity", cascade="all, delete-orphan")
    source_relationships = relationship(
        "EntityRelationshipModel",
        foreign_keys="EntityRelationshipModel.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )
    target_relationships = relationship(
        "EntityRelationshipModel",
        foreign_keys="EntityRelationshipModel.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan",
    )


class EntityRelationshipModel(Base):
    """Relationships between entities (equipment->unit, doc->entity, etc.)."""
    __tablename__ = "entity_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_entity_id = Column(String(255), ForeignKey("entities.entity_id", ondelete="CASCADE"),
                              nullable=False, index=True)
    target_entity_id = Column(String(255), ForeignKey("entities.entity_id", ondelete="CASCADE"),
                              nullable=False, index=True)
    relationship_type = Column(String(64), nullable=False)  # BELONGS_TO, REFERENCES, SUPERSEDES, etc.
    confidence = Column(Float, default=1.0)
    source_document_id = Column(String(255), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    source_entity = relationship("EntityModel", foreign_keys=[source_entity_id],
                                 back_populates="source_relationships")
    target_entity = relationship("EntityModel", foreign_keys=[target_entity_id],
                                 back_populates="target_relationships")


class ChunkEntityModel(Base):
    """Links chunks to canonical entities with confidence scores."""
    __tablename__ = "chunk_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(String(255), ForeignKey("chunks.chunk_id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id = Column(String(255), ForeignKey("entities.entity_id", ondelete="CASCADE"), nullable=False, index=True)
    confidence = Column(Float, default=1.0)

    chunk = relationship("ChunkModel", back_populates="chunk_entities")
    entity = relationship("EntityModel", back_populates="chunk_links")


class IngestionJobModel(Base):
    """Tracks async ingestion job lifecycle."""
    __tablename__ = "ingestion_jobs"

    job_id = Column(String(255), primary_key=True)
    source_id = Column(String(255), ForeignKey("sources.source_id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(32), nullable=False, default=JobStatus.ACCEPTED.value, index=True)
    progress = Column(Float, default=0.0)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=True)
    file_size_bytes = Column(Integer, default=0)
    celery_task_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    security_summary = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)


class SecurityFindingModel(Base):
    """Individual security findings from the security pipeline."""
    __tablename__ = "security_findings"

    finding_id = Column(String(255), primary_key=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(255), ForeignKey("ingestion_jobs.job_id", ondelete="SET NULL"), nullable=True, index=True)
    finding_type = Column(String(32), nullable=False, index=True)  # MALWARE, PROMPT_INJECTION, etc.
    severity = Column(String(16), nullable=False, default=FindingSeverity.LOW.value, index=True)
    description = Column(Text, nullable=False)
    details_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document = relationship("DocumentModel", back_populates="security_findings")


class MetadataModel(Base):
    """Indexed metadata key-value attributes for documents."""
    __tablename__ = "metadata_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(128), nullable=False, index=True)
    value = Column(Text, nullable=False)


class AuditRecordModel(Base):
    """Append-only audit trail for all system actions."""
    __tablename__ = "audit_records"

    record_id = Column(String(255), primary_key=True)
    action = Column(String(128), nullable=False, index=True)
    actor = Column(String(255), nullable=True)
    document_id = Column(String(255), nullable=True, index=True)
    details_json = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


# ============================================================
# DATABASE CONNECTION MANAGER
# ============================================================

class DatabaseSessionManager:
    """Database connection and session factory with fallback support."""

    def __init__(self, uri: str = config.POSTGRES_URI):
        self.uri = uri
        self._engine = None
        self._session_factory = None

    def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._engine is not None:
            return

        try:
            logger.info(f"Connecting to database: {self.uri.split('@')[-1] if '@' in self.uri else self.uri}")
            self._engine = create_engine(
                self.uri,
                pool_size=config.DB_POOL_SIZE,
                max_overflow=config.DB_MAX_OVERFLOW,
                pool_pre_ping=True,
            )
            with self._engine.connect() as conn:
                pass
            logger.info("Successfully connected to primary PostgreSQL database.")
        except Exception as e:
            # Check if URI uses 'postgres' hostname that failed DNS resolution
            connected = False
            if "@postgres:" in self.uri or "@postgres/" in self.uri:
                try:
                    fallback_uri = self.uri.replace("@postgres:", "@localhost:").replace("@postgres/", "@localhost/")
                    logger.warning(f"Failed to resolve host 'postgres' ({e}). Retrying with '{fallback_uri.split('@')[-1]}'")
                    self._engine = create_engine(
                        fallback_uri,
                        pool_size=config.DB_POOL_SIZE,
                        max_overflow=config.DB_MAX_OVERFLOW,
                        pool_pre_ping=True,
                    )
                    with self._engine.connect() as conn:
                        pass
                    self.uri = fallback_uri
                    logger.info("Successfully connected to PostgreSQL at localhost.")
                    connected = True
                except Exception as ex2:
                    logger.warning(f"PostgreSQL connection at localhost also failed: {ex2}")

            if not connected:
                logger.warning(f"PostgreSQL connection failed ({e}). Falling back to SQLite in-memory database.")
                self.uri = "sqlite:///:memory:"
                self._engine = create_engine(self.uri, connect_args={"check_same_thread": False})

        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False)
        
        # Ensure pgvector extension and auto-migrate missing table columns
        try:
            with self._engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
                conn.commit()
                # Migration queries for documents and chunks table
                migrations = [
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS checksum VARCHAR(64);",
                    "ALTER TABLE documents ALTER COLUMN checksum DROP NOT NULL;",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS title VARCHAR(255);",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_id VARCHAR(255);",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_type VARCHAR(64);",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS department VARCHAR(128);",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS plant VARCHAR(128);",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS unit VARCHAR(64);",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS equipment_id VARCHAR(128);",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS version VARCHAR(64) DEFAULT '1.0';",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'PENDING';",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS trust_level VARCHAR(32) DEFAULT 'UNTRUSTED';",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS risk_score FLOAT DEFAULT 0.0;",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS risk_level VARCHAR(16) DEFAULT 'LOW';",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_uri TEXT;",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;",
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS approved_by VARCHAR(255);",
                    "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS trust_level VARCHAR(32) DEFAULT 'UNTRUSTED';",
                    "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding vector(1024);",
                    "ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS progress FLOAT DEFAULT 0.0;",
                ]

                for query in migrations:
                    try:
                        conn.execute(text(query))
                    except Exception as ex:
                        logger.debug(f"Migration statement ignored: {ex}")
                conn.commit()
        except Exception as e:
            logger.warning(f"Database schema auto-migration notice: {e}")

        Base.metadata.create_all(bind=self._engine)


    def get_session(self) -> Session:
        """Create a new database session."""
        if self._session_factory is None:
            self.initialize()
        return self._session_factory()


# Global DB manager singleton
db_manager = DatabaseSessionManager()


def get_db_session() -> Generator[Session, None, None]:
    """Dependency helper providing a transactional session context."""
    session = db_manager.get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
