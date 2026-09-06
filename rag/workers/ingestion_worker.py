"""
Celery worker task for async document ingestion, security validation, extraction, chunking, embedding, and indexing.
"""

import logging
import uuid
import json
from typing import Any, Dict, Optional
from celery import Task

from rag.workers.celery_app import celery_app
from rag.storage.postgres import db_manager, JobStatus, DocumentStatus, TrustLevel
from rag.storage.repositories.job_repo import JobRepository
from rag.storage.repositories.document_repo import DocumentRepository
from rag.storage.repositories.chunk_repo import ChunkRepository
from rag.storage.repositories.security_repo import SecurityRepository
from rag.storage.repositories.audit_repo import AuditRepository
from rag.storage.minio_storage import minio_client
from rag.security.pipeline import SecurityPipeline
from rag.processing.parser import DocumentParser
from rag.chunking.semantic_chunker import SemanticChunker
from rag.embeddings.embedder import BGEM3Embedder, Embedder
from rag.enrichment.entity_extractor import EntityExtractor
from rag.enrichment.entity_linker import EntityLinker
from rag.enrichment.relationships import RelationshipExtractor
from rag.storage.pgvector import PgVectorStore
from rag.retrieval.postgres_fts import PostgresFTSSearch

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="rag.workers.ingestion_worker.process_ingestion_job", max_retries=2)
def process_ingestion_job(
    self: Task,
    job_id: str,
    file_bytes_base64: str,
    filename: str,
    source_id: str = "admin_upload",
    source_type: str = "ADMIN_UPLOAD",
    operator_role: str = "ADMIN",
    metadata_json: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Async Celery task to execute security screening and ingest document into PostgreSQL, MinIO, pgvector & FTS.
    """
    import base64

    logger.info(f"Starting async ingestion task for job_id={job_id}, filename={filename}")

    job_repo = JobRepository()
    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()
    security_repo = SecurityRepository()
    audit_repo = AuditRepository()
    sec_pipeline = SecurityPipeline()
    parser = DocumentParser()
    chunker = SemanticChunker()
    embedder = BGEM3Embedder()
    entity_extractor = EntityExtractor()
    entity_linker = EntityLinker()
    rel_extractor = RelationshipExtractor()
    pgvector_store = PgVectorStore(dimension=embedder.dimension, db_manager=db_manager)
    fts_search = PostgresFTSSearch(db_manager=db_manager)

    file_bytes = base64.b64decode(file_bytes_base64)
    meta_dict = json.loads(metadata_json) if metadata_json else {}

    session = None
    try:
        session = db_manager.get_session()

        # 1. Update job status to PROCESSING
        job_repo.update_status(session, job_id, JobStatus.PROCESSING, progress=0.1)
        audit_repo.record_action(
            session=session,
            action="INGESTION_STARTED",
            job_id=job_id,
            details={"filename": filename, "source_id": source_id},
        )

        # 2. Run Security Pipeline
        sec_result = sec_pipeline.process_file(
            file_bytes=file_bytes,
            filename=filename,
            source_id=source_id,
            source_type=source_type,
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

        # Persist Security Findings
        for finding in sec_result.findings:
            security_repo.add_finding(
                session=session,
                finding_type=finding.finding_type.value,
                severity=finding.severity.value,
                description=finding.description,
                document_id=document_id,
                details=finding.details,
            )

        job_repo.update_status(session, job_id, JobStatus.PROCESSING, progress=0.3)

        # 3. Check Quarantine / Rejection Gate
        if sec_result.gate_decision in ("QUARANTINED", "REJECTED"):
            # Store in MinIO Quarantine bucket
            q_uri = minio_client.upload_raw_document(
                file_bytes=file_bytes,
                filename=filename,
                document_id=document_id,
                bucket_name="quarantine",
            )
            # Create Document record as QUARANTINED / REJECTED
            doc_repo.create_document(
                session=session,
                document_id=document_id,
                title=filename,
                status=doc_status,
                trust_level=sec_result.trust_level,
                risk_score=sec_result.risk_score,
                risk_level=sec_result.risk_level,
                storage_uri=q_uri,
                source_id=source_id,
            )
            job_repo.update_status(
                session=session,
                job_id=job_id,
                status=JobStatus.FAILED if sec_result.gate_decision == "REJECTED" else JobStatus.QUARANTINED,
                progress=1.0,
                error_message=f"Security gate decision: {sec_result.gate_decision}. Risk score: {sec_result.risk_score}",
            )
            audit_repo.record_action(
                session=session,
                action=f"DOCUMENT_{sec_result.gate_decision}",
                document_id=document_id,
                job_id=job_id,
                details={"risk_score": sec_result.risk_score, "findings_count": len(sec_result.findings)},
            )
            session.commit()
            return {
                "job_id": job_id,
                "document_id": document_id,
                "status": sec_result.gate_decision,
                "risk_score": sec_result.risk_score,
                "chunks_indexed": 0,
            }

        # 4. Save trusted raw document to MinIO
        storage_uri = minio_client.upload_raw_document(
            file_bytes=file_bytes,
            filename=filename,
            document_id=document_id,
            bucket_name="trusted",
        )

        # 5. Extract Document Content & Metadata
        job_repo.update_status(session, job_id, JobStatus.PROCESSING, progress=0.5)
        parsed_doc = parser.parse_bytes(file_bytes, filename=filename)

        # Create Active/Review Document record
        doc_record = doc_repo.create_document(
            session=session,
            document_id=document_id,
            title=filename,
            status=doc_status,
            trust_level=sec_result.trust_level,
            risk_score=sec_result.risk_score,
            risk_level=sec_result.risk_level,
            storage_uri=storage_uri,
            source_id=source_id,
            metadata_dict=parsed_doc.metadata or meta_dict,
        )

        # 6. Chunk Document Text
        job_repo.update_status(session, job_id, JobStatus.PROCESSING, progress=0.7)
        chunks = chunker.chunk_text(
            document_id=document_id,
            text=parsed_doc.content,
            page_number=1,
            section_title="General",
        )

        # 7. Generate Vectors, Extract Entities & Persist Chunks
        chunk_records = []
        texts_to_embed = [c.content for c in chunks]
        embeddings = embedder.embed_batch(texts_to_embed)

        for chunk_obj, vec in zip(chunks, embeddings):
            chunk_obj.metadata["trust_level"] = sec_result.trust_level
            chunk_obj.metadata["status"] = doc_status

            # Persist Chunk in DB
            c_rec = chunk_repo.create_chunk(
                session=session,
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
            chunk_records.append(c_rec)

            # Extract & Link Entities
            extracted_ents = entity_extractor.extract_entities(chunk_obj.content)
            entity_linker.link_entities_for_chunk(
                chunk_id=chunk_obj.chunk_id,
                extracted_entities=extracted_ents,
                session=session,
            )

            # Insert into native pgvector
            pgvector_store.insert_chunk_vector(chunk_obj, vec, session=session)

        # 8. Extract Document Relationships
        rel_extractor.extract_relationships(source_doc_id=document_id, text=parsed_doc.content, session=session)

        # 9. Update Ingestion Job to COMPLETED
        job_repo.update_status(session, job_id, JobStatus.COMPLETED, progress=1.0, document_id=document_id)
        audit_repo.record_action(
            session=session,
            action="INGESTION_COMPLETED",
            document_id=document_id,
            job_id=job_id,
            details={"chunks_count": len(chunks), "trust_level": sec_result.trust_level},
        )
        session.commit()

        logger.info(f"Successfully processed ingestion job {job_id} with {len(chunks)} chunks.")
        return {
            "job_id": job_id,
            "document_id": document_id,
            "status": "COMPLETED",
            "trust_level": sec_result.trust_level,
            "chunks_indexed": len(chunks),
        }

    except Exception as e:
        logger.error(f"Error in process_ingestion_job for {job_id}: {e}", exc_info=True)
        if session:
            session.rollback()
            try:
                job_repo.update_status(
                    session=session,
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    progress=1.0,
                    error_message=str(e),
                )
                session.commit()
            except Exception:
                pass
        raise e
    finally:
        if session:
            session.close()
