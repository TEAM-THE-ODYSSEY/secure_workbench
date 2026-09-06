"""
Enrichment package for metadata management, entity extraction, relationships, and document versioning.
"""

from rag.enrichment.metadata import DocumentMetadata, MetadataEnricher
from rag.enrichment.entity_extractor import EntityExtractor, ExtractedEntity, EntityType
from rag.enrichment.relationships import RelationshipExtractor, DocumentRelationship, RelationshipType
from rag.enrichment.versioning import DocumentVersionManager, DocumentVersionRecord

__all__ = [
    "DocumentMetadata",
    "MetadataEnricher",
    "EntityExtractor",
    "ExtractedEntity",
    "EntityType",
    "RelationshipExtractor",
    "DocumentRelationship",
    "RelationshipType",
    "DocumentVersionManager",
    "DocumentVersionRecord",
]
