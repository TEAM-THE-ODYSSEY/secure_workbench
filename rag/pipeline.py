"""
Main RAG Orchestration Layer exposing INGESTION pipeline and QUERY pipeline.
Integrates Security Pipeline, MinIO Object Storage, PostgreSQL pgvector, FTS, Entity Linker, and Celery async dispatch.
"""

import logging
import os
import uuid
import json
import base64
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from rag.config import config, RAGConfig
from rag.ingestion.connectors.file_connector import FileConnector, RawIngestedDocument
from rag.ingestion.change_detector import ChangeDetector, DocumentChangeState
from rag.processing.parser import DocumentParser, ParsedDocument
from rag.processing.cleaner import TextCleaner
from rag.processing.structure import StructureExtractor
from rag.enrichment.metadata import MetadataEnricher, DocumentMetadata
from rag.enrichment.entity_extractor import EntityExtractor
from rag.enrichment.entity_linker import EntityLinker
from rag.enrichment.relationships import RelationshipExtractor
from rag.enrichment.versioning import DocumentVersionManager, DocumentVersionRecord
from rag.chunking.semantic_chunker import SemanticChunker, Chunk
from rag.chunking.structure_chunker import StructureAwareChunker
from rag.embeddings.embedder import BGEM3Embedder, Embedder, BaseEmbedder
from rag.storage.postgres import db_manager, JobStatus, DocumentStatus, TrustLevel
from rag.storage.repositories.job_repo import JobRepository
from rag.storage.repositories.source_repo import SourceRepository
from rag.storage.repositories.document_repo import DocumentRepository
from rag.storage.repositories.chunk_repo import ChunkRepository
from rag.storage.repositories.security_repo import SecurityRepository
from rag.storage.repositories.audit_repo import AuditRepository
from rag.storage.pgvector import PgVectorStore
from rag.storage.minio_storage import minio_client
from rag.security.pipeline import SecurityPipeline

from rag.retrieval.query_parser import QueryParser, ParsedQuery
from rag.retrieval.metadata_filter import MetadataFilter, FilterCondition
from rag.retrieval.vector_search import VectorSearch
from rag.retrieval.keyword_search import KeywordSearch
from rag.retrieval.postgres_fts import PostgresFTSSearch
from rag.retrieval.trust_filter import TrustFilter
from rag.retrieval.hybrid_search import HybridSearch
from rag.retrieval.reranker import BGEReranker, Reranker, ReciprocalReranker
from rag.context.context_builder import ContextBuilder, GroundedContextResult

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """INGESTION PIPELINE with security screening, entity linking, and MinIO/PostgreSQL storage."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        metadata_enricher: Optional[MetadataEnricher] = None,
        entity_extractor: Optional[EntityExtractor] = None,
        entity_linker: Optional[EntityLinker] = None,
        version_manager: Optional[DocumentVersionManager] = None,
        chunker: Optional[SemanticChunker] = None,
        embedder: Optional[BaseEmbedder] = None,
        vector_store: Optional[PgVectorStore] = None,
        fts_search: Optional[PostgresFTSSearch] = None,
        security_pipeline: Optional[SecurityPipeline] = None,
    ):
        self.parser = parser or DocumentParser()
        self.metadata_enricher = metadata_enricher or MetadataEnricher()
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.entity_linker = entity_linker or EntityLinker()
        self.version_manager = version_manager or DocumentVersionManager()
        self.chunker = chunker or SemanticChunker(target_chunk_size=config.DEFAULT_CHUNK_SIZE)
        self.embedder = embedder or BGEM3Embedder()
        self.vector_store = vector_store or PgVectorStore(dimension=self.embedder.dimension, db_manager=db_manager)
        self.fts_search = fts_search or PostgresFTSSearch(db_manager=db_manager)
        self.security_pipeline = security_pipeline or SecurityPipeline()
        self.rel_extractor = RelationshipExtractor()

    def ingest_bytes_sync(
        self,
        content_bytes: bytes,
        filename: str,
        source_id: str = "admin_upload",
        operator_role: str = "ADMIN",
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synchronously ingest document through security pipeline, extraction, chunking, and indexing."""
        logger.info(f"--- Starting Sync Ingestion for: {filename} ({source_id}) ---")

        # 1. Run Security Pipeline
        sec_result = self.security_pipeline.process_file(
            file_bytes=content_bytes,
            filename=filename,
            source_id=source_id,
            operator_role=operator_role,
        )

        document_id = sec_result.document_id
        doc_status = DocumentStatus.PENDING.value
        if sec_result.gate_decision == "APPROVED":
            doc_status = DocumentStatus.APPROVED.value
        elif sec_result.gate_decision == "REVIEW_REQUIRED":

            doc_status = DocumentStatus.REVIEW_REQUIRED.value
        elif sec_result.gate_decision == "QUARANTINED":
            doc_status = DocumentStatus.QUARANTINED.value
        elif sec_result.gate_decision == "REJECTED":
            doc_status = DocumentStatus.REJECTED.value

        # 2. Check Security Gate
        if sec_result.gate_decision in ("QUARANTINED", "REJECTED"):
            logger.warning(f"Document {filename} blocked by Security Gate: decision={sec_result.gate_decision}")
            q_uri = minio_client.upload_raw_document(
                file_bytes=content_bytes,
                filename=filename,
                document_id=document_id,
                bucket_name="quarantine",
            )
            return {
                "document_id": document_id,
                "status": doc_status,
                "trust_level": sec_result.trust_level,
                "risk_score": sec_result.risk_score,
                "gate_decision": sec_result.gate_decision,
                "chunks_indexed": 0,
                "storage_uri": q_uri,
            }

        # 3. Store in MinIO Trusted bucket
        storage_uri = minio_client.upload_raw_document(
            file_bytes=content_bytes,
            filename=filename,
            document_id=document_id,
            bucket_name="trusted",
        )

        # 4. Parse content
        parsed_doc = self.parser.parse_bytes(content_bytes, filename=filename)

        # Persist DocumentModel to PostgreSQL database
        db_sess = db_manager.get_session()
        try:
            doc_repo = DocumentRepository(session=db_sess)
            doc_repo.create_document(
                session=db_sess,
                document_id=document_id,
                title=filename,
                status=doc_status,
                trust_level=sec_result.trust_level,
                risk_score=sec_result.risk_score,
                risk_level=getattr(sec_result, "risk_level", "LOW"),
                storage_uri=storage_uri,
                source_id=source_id,
                metadata_dict=custom_metadata,
            )
            db_sess.commit()
        except Exception as ex:
            logger.warning(f"Could not persist DocumentModel in sync ingestion: {ex}")
            db_sess.rollback()
        finally:
            db_sess.close()

        # 5. Chunking
        chunks = self.chunker.chunk_text(
            document_id=document_id,
            text=parsed_doc.content,
            page_number=1,
            section_title="General",
        )

        # 6. Embedding & Indexing
        texts = [c.content for c in chunks]
        embeddings = self.embedder.embed_batch(texts)

        chunk_repo = ChunkRepository()
        for chunk_obj, vec in zip(chunks, embeddings):
            chunk_obj.metadata["trust_level"] = sec_result.trust_level
            chunk_obj.metadata["status"] = doc_status
            chunk_obj.embedding = vec

            # Save Chunk record to PostgreSQL DB
            c_sess = db_manager.get_session()
            try:
                chunk_repo_db = ChunkRepository(session=c_sess)
                chunk_repo_db.create_chunk(
                    session=c_sess,
                    chunk_id=chunk_obj.chunk_id,
                    document_id=document_id,
                    content=chunk_obj.content,
                    page_number=chunk_obj.page_number,
                    section_title=chunk_obj.section_title,
                    chunk_index=chunk_obj.chunk_index,
                    trust_level=sec_result.trust_level,
                    metadata_dict=chunk_obj.metadata,
                    embedding_json=vec,
                )
                c_sess.commit()
            except Exception as ex:
                logger.warning(f"Could not save ChunkModel DB record: {ex}")
                c_sess.rollback()
            finally:
                c_sess.close()

            self.vector_store.insert_chunk_vector(chunk_obj, vec)
            self.fts_search.add_chunk(chunk_obj)

            # Entity extraction & linking
            extracted_ents = self.entity_extractor.extract_entities(chunk_obj.content)
            self.entity_linker.link_entities_for_chunk(
                chunk_id=chunk_obj.chunk_id,
                extracted_entities=extracted_ents,
            )

        logger.info(f"--- Successfully Ingested Sync: {filename} ({len(chunks)} chunks indexed) ---")
        return {
            "document_id": document_id,
            "status": doc_status,
            "trust_level": sec_result.trust_level,
            "risk_score": sec_result.risk_score,
            "gate_decision": sec_result.gate_decision,
            "chunks_indexed": len(chunks),
            "storage_uri": storage_uri,
        }


class QueryPipeline:
    """QUERY PIPELINE: Query Parser -> Metadata & Trust Filtering -> Hybrid Retrieval -> Reranking -> Grounded Context"""

    def __init__(
        self,
        query_parser: Optional[QueryParser] = None,
        hybrid_search: Optional[HybridSearch] = None,
        reranker: Optional[Reranker] = None,
        context_builder: Optional[ContextBuilder] = None,
    ):
        self.query_parser = query_parser or QueryParser()
        self.hybrid_search = hybrid_search
        self.reranker = reranker or BGEReranker()
        self.context_builder = context_builder or ContextBuilder()

    def execute_query(
        self,
        user_query: str,
        filter_override: Optional[FilterCondition] = None,
        top_k: int = config.DEFAULT_TOP_K,
    ) -> GroundedContextResult:
        """Execute full query retrieval, fusion, trust filtering, reranking, and context construction."""
        logger.info(f"=== Executing Query Pipeline for: '{user_query}' ===")

        # 1. Query Parsing
        parsed_query: ParsedQuery = self.query_parser.parse(user_query)

        # 2. Metadata Filtering
        effective_filters = filter_override
        if not effective_filters and parsed_query.inferred_filters:
            effective_filters = FilterCondition(**parsed_query.inferred_filters)

        # 3. Hybrid Retrieval (Vector + FTS + Trust Filtering + Reranking)
        if not self.hybrid_search:
            raise RuntimeError("HybridSearch component not configured in QueryPipeline!")

        candidate_chunks: List[Tuple[Chunk, float]] = self.hybrid_search.search(
            query_text=parsed_query.clean_query,
            top_k=top_k,
            filter_condition=effective_filters,
        )

        # 4. Context Building
        result: GroundedContextResult = self.context_builder.build_grounded_context(
            query=user_query,
            scored_chunks=candidate_chunks,
        )

        logger.info(f"=== Query Pipeline Complete. Grounded Context ready ({len(result.citations)} citations). ===")
        return result


class RAGPipeline:
    """Facade class wrapping INGESTION and QUERY pipelines into a unified entry point."""

    def __init__(self):
        self.embedder = BGEM3Embedder()
        self.vector_store = PgVectorStore(dimension=self.embedder.dimension, db_manager=db_manager)
        self.fts_search = PostgresFTSSearch(db_manager=db_manager)
        self.trust_filter = TrustFilter()
        self.reranker = BGEReranker()

        self.vector_search = VectorSearch(embedder=self.embedder, vector_store=self.vector_store)
        self.hybrid_search = HybridSearch(
            vector_search=self.vector_search,
            keyword_search=self.fts_search,
            trust_filter=self.trust_filter,
            reranker=self.reranker,
        )

        self.ingestion = IngestionPipeline(
            embedder=self.embedder,
            vector_store=self.vector_store,
            fts_search=self.fts_search,
        )
        self.query = QueryPipeline(
            hybrid_search=self.hybrid_search,
            reranker=self.reranker,
        )
        self._ensure_seeded()

    def _ensure_seeded(self) -> None:
        """Seed baseline refinery knowledge chunks if in-memory store is unpopulated."""
        if not PgVectorStore._global_vector_store:
            try:
                self.ingestion.ingest_bytes_sync(
                    content_bytes=b"MRPL Health and Safety Report outlines refinery safety recognitions (National Safety Council Apex Safety Award, OISD Award), accident-free man-hour milestones, H2S monitor rules, and SCBA compliance across CDU-1 processing units.",
                    filename="Health_And_Safety.txt",
                    source_id="seed_initial_safety",
                )
                self.ingestion.ingest_bytes_sync(
                    content_bytes=b"Crude Feed Charge Pump P-101A operates in CDU-1. Normal operating vibration limit is below 4.0 mm/s. Maximum operating temperature 345 C. In case of elevated vibration (6.8 mm/s), switch to standby pump P-101B and isolate XV-101.",
                    filename="SOP-23_P101A.txt",
                    source_id="seed_initial_sop23",
                )
                logger.info("Auto-seeded baseline Knowledge Base documents into shared RAG store.")
            except Exception as e:
                logger.warning(f"Could not auto-seed baseline documents: {e}")

    def ingest_bytes_async(
        self,
        content_bytes: bytes,
        filename: str,
        source_id: str = "admin_upload",
        operator_role: str = "ADMIN",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Dispatch async ingestion job to Celery background task."""
        from rag.workers.ingestion_worker import process_ingestion_job

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        session = None
        try:
            session = db_manager.get_session()
            job_repo = JobRepository()

            # Create IngestionJob record
            job_record = job_repo.create_job(
                session=session,
                job_id=job_id,
                filename=filename,
                source_id=source_id,
                status=JobStatus.PENDING,
            )
            session.commit()

            # Encode bytes to base64 for JSON Celery serialization
            b64_bytes = base64.b64encode(content_bytes).decode("utf-8")
            meta_json = json.dumps(metadata) if metadata else None

            # Dispatch Celery task
            process_ingestion_job.delay(
                job_id=job_id,
                file_bytes_base64=b64_bytes,
                filename=filename,
                source_id=source_id,
                operator_role=operator_role,
                metadata_json=meta_json,
            )

            return {
                "job_id": job_id,
                "status": "PENDING",
                "message": f"Async ingestion job {job_id} queued successfully.",
            }
        except Exception as e:
            logger.error(f"Error queueing async ingestion job: {e}")
            if session:
                session.rollback()
            # Fallback to sync ingestion if Celery/Broker fails
            logger.info("Falling back to synchronous ingestion execution...")
            sync_res = self.ingestion.ingest_bytes_sync(
                content_bytes=content_bytes,
                filename=filename,
                source_id=source_id,
                operator_role=operator_role,
                custom_metadata=metadata,
            )
            return {
                "job_id": job_id,
                "status": sync_res.get("status", "COMPLETED"),
                "message": "Processed synchronously (Broker offline fallback).",
                "details": sync_res,
            }
        finally:
            if session:
                session.close()

    def ingest_bytes(
        self,
        content_bytes: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Synchronous ingestion helper."""
        return self.ingestion.ingest_bytes_sync(
            content_bytes=content_bytes,
            filename=filename,
            custom_metadata=metadata,
        )

    def query_context(
        self,
        user_query: str,
        top_k: int = 5,
        filters: Optional[FilterCondition] = None,
    ) -> GroundedContextResult:
        """Run query retrieval pipeline with hybrid search, trust gate, and reranking."""
        return self.query.execute_query(user_query=user_query, filter_override=filters, top_k=top_k)
