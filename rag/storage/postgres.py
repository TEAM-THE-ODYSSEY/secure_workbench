"""
PostgreSQL database connection, session abstraction, and SQLAlchemy ORM schemas.
"""

from datetime import datetime, timezone
import logging
from typing import Generator, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

from rag.config import config

logger = logging.getLogger(__name__)

Base = declarative_base()


class DocumentModel(Base):
    """SQLAlchemy model for ingested documents."""
    __tablename__ = "documents"

    id = Column(String(255), primary_key=True)
    source_id = Column(String(512), unique=True, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    extension = Column(String(32), nullable=False)
    document_type = Column(String(64), index=True)
    department = Column(String(128), index=True)
    plant = Column(String(128), index=True)
    unit = Column(String(128), index=True)
    equipment_id = Column(String(128), index=True)
    checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    versions = relationship("DocumentVersionModel", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("ChunkModel", back_populates="document", cascade="all, delete-orphan")


class DocumentVersionModel(Base):
    """SQLAlchemy model for document version control."""
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
    """SQLAlchemy model for document chunks and vector representations."""
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
    metadata_json = Column(JSON, default=dict)
    
    # Store embedding as JSON array if pgvector not active, or Vector column
    embedding_json = Column(JSON, nullable=True)

    document = relationship("DocumentModel", back_populates="chunks")


class MetadataModel(Base):
    """SQLAlchemy model for indexed metadata key-value attributes."""
    __tablename__ = "metadata_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(128), nullable=False, index=True)
    value = Column(Text, nullable=False)


class DatabaseSessionManager:
    """Database connection and session factory."""

    def __init__(self, uri: str = config.POSTGRES_URI):
        self.uri = uri
        self._engine = None
        self._session_factory = None

    def initialize(self) -> None:
        """Initialize database engine and session factory with fallback to SQLite in-memory if Postgres is unavailable."""
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
            # Try connecting
            with self._engine.connect() as conn:
                pass
            logger.info("Successfully connected to primary PostgreSQL database.")
        except Exception as e:
            if config.USE_IN_MEMORY_FALLBACK:
                logger.warning(f"Failed to connect to primary Postgres DB ({e}). Falling back to SQLite in-memory database.")
                self.uri = "sqlite:///:memory:"
                self._engine = create_engine(self.uri, connect_args={"check_same_thread": False})
            else:
                raise e

        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False)
        
        # Auto-create tables for development/standalone run
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
