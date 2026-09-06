"""
Storage package for relational PostgreSQL database, pgvector vector search, object storage, and repository pattern layers.
"""

from rag.storage.postgres import (
    DatabaseSessionManager,
    get_db_session,
    Base,
    SourceModel,
    DocumentModel,
    DocumentVersionModel,
    ChunkModel,
    EntityModel,
    EntityRelationshipModel,
    ChunkEntityModel,
    IngestionJobModel,
    SecurityFindingModel,
    MetadataModel,
    AuditRecordModel,
    SourceType,
    TrustLevel,
    DocumentStatus,
    JobStatus,
    RiskLevel,
    FindingType,
    FindingSeverity,
)
from rag.storage.pgvector import PgVectorStore
from rag.storage.object_storage import ObjectStorage, LocalObjectStorage
from rag.storage.repositories.document_repo import DocumentRepository
from rag.storage.repositories.chunk_repo import ChunkRepository
from rag.storage.repositories.metadata_repo import MetadataRepository
from rag.storage.repositories.source_repo import SourceRepository
from rag.storage.repositories.job_repo import JobRepository
from rag.storage.repositories.entity_repo import EntityRepository
from rag.storage.repositories.security_repo import SecurityRepository
from rag.storage.repositories.audit_repo import AuditRepository

__all__ = [
    # Connection
    "DatabaseSessionManager",
    "get_db_session",
    "Base",
    # ORM Models
    "SourceModel",
    "DocumentModel",
    "DocumentVersionModel",
    "ChunkModel",
    "EntityModel",
    "EntityRelationshipModel",
    "ChunkEntityModel",
    "IngestionJobModel",
    "SecurityFindingModel",
    "MetadataModel",
    "AuditRecordModel",
    # Enums
    "SourceType",
    "TrustLevel",
    "DocumentStatus",
    "JobStatus",
    "RiskLevel",
    "FindingType",
    "FindingSeverity",
    # Storage
    "PgVectorStore",
    "ObjectStorage",
    "LocalObjectStorage",
    # Repositories
    "DocumentRepository",
    "ChunkRepository",
    "MetadataRepository",
    "SourceRepository",
    "JobRepository",
    "EntityRepository",
    "SecurityRepository",
    "AuditRepository",
]
