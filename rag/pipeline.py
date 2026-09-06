"""
Main RAG Orchestration Layer exposing INGESTION pipeline and QUERY pipeline.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from rag.config import config, RAGConfig
from rag.ingestion.connectors.file_connector import FileConnector, RawIngestedDocument
from rag.ingestion.change_detector import ChangeDetector, DocumentChangeState
from rag.processing.parser import DocumentParser, ParsedDocument
from rag.processing.cleaner import TextCleaner
from rag.processing.structure import StructureExtractor
from rag.enrichment.metadata import MetadataEnricher, DocumentMetadata
from rag.enrichment.entity_extractor import EntityExtractor
from rag.enrichment.relationships import RelationshipExtractor
from rag.enrichment.versioning import DocumentVersionManager, DocumentVersionRecord
from rag.chunking.semantic_chunker import SemanticChunker, Chunk
from rag.chunking.structure_chunker import StructureAwareChunker
from rag.chunking.parent_child import ParentChildChunker
from rag.embeddings.embedder import Embedder, BaseEmbedder
from rag.embeddings.model import EmbeddingModelConfig
from rag.storage.pgvector import PgVectorStore
from rag.storage.object_storage import LocalObjectStorage, ObjectStorage
from rag.storage.repositories.document_repo import DocumentRepository
from rag.storage.repositories.chunk_repo import ChunkRepository
from rag.storage.repositories.metadata_repo import MetadataRepository

from rag.retrieval.query_parser import QueryParser, ParsedQuery
from rag.retrieval.metadata_filter import MetadataFilter, FilterCondition
from rag.retrieval.vector_search import VectorSearch
from rag.retrieval.keyword_search import KeywordSearch
from rag.retrieval.hybrid_search import HybridSearch
from rag.retrieval.reranker import CrossEncoderReranker, Reranker, ReciprocalReranker
from rag.context.deduplicator import ContextDeduplicator
from rag.context.context_builder import ContextBuilder, GroundedContextResult
from rag.context.citation_builder import CitationBuilder
from rag.context.context_compressor import ContextCompressor

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """INGESTION PIPELINE:
    Raw Document -> Loader -> Parser -> Cleaner -> Structure Extraction
    -> Metadata/Entity Enrichment -> Chunking -> Embedding -> Storage
    """

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        metadata_enricher: Optional[MetadataEnricher] = None,
        entity_extractor: Optional[EntityExtractor] = None,
        version_manager: Optional[DocumentVersionManager] = None,
        chunker: Optional[StructureAwareChunker] = None,
        embedder: Optional[BaseEmbedder] = None,
        vector_store: Optional[PgVectorStore] = None,
        object_storage: Optional[ObjectStorage] = None,
        document_repo: Optional[DocumentRepository] = None,
        chunk_repo: Optional[ChunkRepository] = None,
        metadata_repo: Optional[MetadataRepository] = None,
        keyword_search: Optional[KeywordSearch] = None,
    ):
        self.parser = parser or DocumentParser()
        self.metadata_enricher = metadata_enricher or MetadataEnricher()
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.version_manager = version_manager or DocumentVersionManager()
        self.chunker = chunker or StructureAwareChunker(max_chunk_tokens=config.DEFAULT_CHUNK_SIZE)
        self.embedder = embedder or Embedder()
        self.vector_store = vector_store or PgVectorStore(dimension=self.embedder.dimension)
        self.object_storage = object_storage or LocalObjectStorage()
        self.document_repo = document_repo or DocumentRepository()
        self.chunk_repo = chunk_repo or ChunkRepository()
        self.metadata_repo = metadata_repo or MetadataRepository()
        self.keyword_search = keyword_search

        # Change detector
        self.change_detector = ChangeDetector()
        self._indexed_chunks: List[Chunk] = []

    def ingest_document(self, raw_doc: RawIngestedDocument, custom_metadata: Optional[Dict[str, Any]] = None) -> DocumentMetadata:
        """Execute complete ingestion pipeline for a single raw document."""
        logger.info(f"--- Starting Ingestion for: {raw_doc.filename} ({raw_doc.source_id}) ---")

        # 1. Change Detection check
        change_res = self.change_detector.detect_change(raw_doc.source_id, raw_doc.checksum)
        if change_res.state == DocumentChangeState.UNCHANGED:
            logger.info(f"Document {raw_doc.filename} is UNCHANGED. Skipping ingestion.")
            doc_model = self.document_repo.get_by_source_id(raw_doc.source_id)
            return self.metadata_enricher.enrich(custom_metadata or {}, raw_doc.filename, "")

        # 2. Persist Raw file in Object Storage
        storage_uri = self.object_storage.save_file(
            file_id=raw_doc.checksum[:16],
            content_bytes=raw_doc.content_bytes,
            filename=raw_doc.filename,
        )

        # 3. Parse Document (Loader -> Parser -> Cleaner -> Structure Extraction)
        parsed_doc: ParsedDocument = self.parser.parse(raw_doc)

        # 4. Knowledge Enrichment (Metadata & Entity Enrichment & Versioning)
        raw_meta = {**(custom_metadata or {}), "storage_uri": storage_uri, "source_id": raw_doc.source_id}
        doc_metadata: DocumentMetadata = self.metadata_enricher.enrich(
            raw_metadata=raw_meta,
            doc_title=parsed_doc.filename,
            full_text=parsed_doc.full_cleaned_text,
        )

        # Register versioning
        ver_record: DocumentVersionRecord = self.version_manager.register_new_version(
            document_id=doc_metadata.document_id,
            revision_code=doc_metadata.revision,
            checksum=raw_doc.checksum,
            change_summary="Initial / updated document ingestion",
        )
        doc_metadata.extra_attributes["version_id"] = ver_record.version_id

        # 5. Entity Extraction
        entities = self.entity_extractor.extract_entities(parsed_doc.full_cleaned_text)
        logger.info(f"Extracted {len(entities)} technical entities from {raw_doc.filename}")

        # 6. Chunking
        chunks: List[Chunk] = self.chunker.chunk_parsed_document(parsed_doc, metadata=doc_metadata)

        # 7. Embedding & Storage
        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedder.embed_batch(chunk_texts)

        for chunk, vec in zip(chunks, embeddings):
            chunk.embedding = vec
            self.vector_store.insert_chunk_vector(chunk, vec)
            self._indexed_chunks.append(chunk)

        # Save to repositories
        self.document_repo.upsert_document(
            metadata=doc_metadata,
            checksum=raw_doc.checksum,
            filename=raw_doc.filename,
            extension=raw_doc.extension,
        )
        self.document_repo.add_version(ver_record)
        self.chunk_repo.save_batch(chunks)
        self.metadata_repo.add_metadata_entries(doc_metadata.document_id, doc_metadata.to_dict())

        # Update Keyword Search index if attached
        if self.keyword_search:
            self.keyword_search.index_chunks(self._indexed_chunks)

        self.change_detector.mark_indexed(raw_doc.source_id, raw_doc.checksum)
        logger.info(f"--- Successfully Ingested: {raw_doc.filename} ({len(chunks)} chunks indexed) ---")
        return doc_metadata

    def ingest_filepath(self, filepath: str, custom_metadata: Optional[Dict[str, Any]] = None) -> Optional[DocumentMetadata]:
        """Convenience method to ingest a file from disk by filepath."""
        connector = FileConnector(filepath)
        raw_doc = connector.fetch_single(filepath)
        if raw_doc:
            return self.ingest_document(raw_doc, custom_metadata=custom_metadata)
        else:
            logger.error(f"Could not load file at path: {filepath}")
            return None


class QueryPipeline:
    """QUERY PIPELINE:
    User Query -> Query Parser -> Metadata Filtering -> Hybrid Retrieval
    -> Reranking -> Deduplication -> Context Building -> Citation Building -> Grounded Context
    """

    def __init__(
        self,
        query_parser: Optional[QueryParser] = None,
        hybrid_search: Optional[HybridSearch] = None,
        reranker: Optional[Reranker] = None,
        context_builder: Optional[ContextBuilder] = None,
    ):
        self.query_parser = query_parser or QueryParser()
        self.hybrid_search = hybrid_search
        self.reranker = reranker or ReciprocalReranker()
        self.context_builder = context_builder or ContextBuilder()

    def set_hybrid_search(self, hybrid_search: HybridSearch) -> None:
        """Attach configured HybridSearch instance."""
        self.hybrid_search = hybrid_search

    def execute_query(
        self,
        user_query: str,
        filter_override: Optional[FilterCondition] = None,
        top_k: int = config.DEFAULT_TOP_K,
    ) -> GroundedContextResult:
        """Execute full query retrieval, fusion, reranking, and context construction pipeline."""
        logger.info(f"=== Executing Query Pipeline for: '{user_query}' ===")

        # 1. Query Parsing (Understand intent, entities, implicit filters)
        parsed_query: ParsedQuery = self.query_parser.parse(user_query)

        # 2. Metadata Filtering resolution
        effective_filters = filter_override
        if not effective_filters and parsed_query.inferred_filters:
            effective_filters = FilterCondition(**parsed_query.inferred_filters)

        # 3. Hybrid Retrieval (Vector + BM25 Keyword Search)
        if not self.hybrid_search:
            raise RuntimeError("HybridSearch component not configured in QueryPipeline!")

        candidate_chunks: List[Tuple[Chunk, float]] = self.hybrid_search.search(
            query_text=parsed_query.clean_query,
            top_k=top_k * 2,
            filter_condition=effective_filters,
        )

        # 4. Reranking
        reranked_chunks: List[Tuple[Chunk, float]] = self.reranker.rerank(
            query=parsed_query.clean_query,
            candidate_chunks=candidate_chunks,
            top_n=top_k,
        )

        # 5. Context Building (Deduplication + Citation Building + Grounded Context)
        result: GroundedContextResult = self.context_builder.build_grounded_context(
            query=user_query,
            scored_chunks=reranked_chunks,
        )

        logger.info(f"=== Query Pipeline Complete. Formatted Grounded Context ready ({len(result.citations)} citations). ===")
        return result


class RAGPipeline:
    """Facade class wrapping INGESTION and QUERY pipelines into a unified entry point."""

    def __init__(self):
        # Shared component instances
        self.embedder = Embedder()
        self.vector_store = PgVectorStore(dimension=self.embedder.dimension)
        self.keyword_search = KeywordSearch()

        # Build retrieval sub-modules
        self.vector_search = VectorSearch(embedder=self.embedder, vector_store=self.vector_store)
        self.hybrid_search = HybridSearch(vector_search=self.vector_search, keyword_search=self.keyword_search)

        # Pipelines
        self.ingestion = IngestionPipeline(
            embedder=self.embedder,
            vector_store=self.vector_store,
            keyword_search=self.keyword_search,
        )
        self.query = QueryPipeline(hybrid_search=self.hybrid_search)

    def ingest_file(self, filepath: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[DocumentMetadata]:
        """Ingest document file."""
        return self.ingestion.ingest_filepath(filepath, custom_metadata=metadata)

    def query_context(self, user_query: str, top_k: int = 5, filters: Optional[FilterCondition] = None) -> GroundedContextResult:
        """Run query retrieval pipeline."""
        return self.query.execute_query(user_query=user_query, filter_override=filters, top_k=top_k)
