"""
Enrichment package for metadata management, entity extraction, canonical entity linking, relationships, and document versioning.
"""

from rag.enrichment.metadata import DocumentMetadata, MetadataEnricher
from rag.enrichment.entity_extractor import EntityExtractor, ExtractedEntity, EntityType
from rag.enrichment.entity_linker import EntityLinker
from rag.enrichment.relationships import RelationshipExtractor, DocumentRelationship, RelationshipType
from rag.enrichment.versioning import DocumentVersionManager, DocumentVersionRecord

__all__ = [
    "DocumentMetadata",
    "MetadataEnricher",
    "EntityExtractor",
    "ExtractedEntity",
    "EntityType",
    "EntityLinker",
    "RelationshipExtractor",
    "DocumentRelationship",
    "RelationshipType",
    "DocumentVersionManager",
    "DocumentVersionRecord",
]
