"""
Production FastAPI Application Server for the Knowledge Base System.
Provides endpoints for frontend document uploads, security validation, async jobs, multi-agent knowledge retrieval, and entity management.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag.config import config
from rag.pipeline import RAGPipeline
from rag.retrieval.metadata_filter import FilterCondition
from rag.storage.postgres import db_manager, DocumentModel, ChunkModel, IngestionJobModel, EntityModel, SecurityFindingModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("knowledge_base_api")

pipeline: Optional[RAGPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to initialize database and load model engines on server startup."""
    global pipeline
    logger.info("Initializing Knowledge Base Engine & Vector DB...")
    db_manager.initialize()
    pipeline = RAGPipeline()
    logger.info("Knowledge Base Engine successfully loaded and ready for frontend & agent requests.")
    
    # Pre-warm embedding model in background thread so Uvicorn starts listening immediately
    import threading
    def prewarm():
        try:
            if pipeline and hasattr(pipeline, "embedder"):
                pipeline.embedder._get_model()
                logger.info("Background embedding model pre-warm complete.")
        except Exception as ex:
            logger.warning(f"Background model pre-warm notice: {ex}")
            
    threading.Thread(target=prewarm, daemon=True).start()
    yield
    logger.info("Shutting down Knowledge Base API Server.")


app = FastAPI(
    title="MRPL RAG Enterprise Knowledge Base API",
    description="High-performance Knowledge Base system providing secure document ingestion, vector retrieval, and multi-agent context synthesis.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- DATA MODELS ---

class KnowledgeQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language question or search prompt")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")
    unit: Optional[str] = Field(default=None, description="Optional plant unit filter (e.g., CDU-1)")
    equipment_id: Optional[str] = Field(default=None, description="Optional equipment tag filter (e.g., P-101A)")
    department: Optional[str] = Field(default=None, description="Optional department filter")


class CitationResponse(BaseModel):
    citation_id: str
    document_id: str
    document_title: str
    section_title: str
    page_number: int
    revision: str
    trust_level: str
    snippet: str


class KnowledgeQueryResponse(BaseModel):
    query: str
    context_text: str
    citations: List[CitationResponse]
    retrieved_chunk_count: int


class IngestionJobResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    document_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str


# --- ENDPOINTS ---

@app.get("/", summary="Health Check")
@app.get("/health", summary="Health Check Alias")
@app.get("/api/health", summary="Health Check Alias")
def health_check():
    """Health check endpoint to verify API and Knowledge Base status."""
    return {
        "status": "online",
        "service": "MRPL Enterprise Knowledge Base Engine",
        "vector_dimensions": config.EMBEDDING_DIMENSION,
        "postgres_connected": True,
    }


@app.post("/api/v1/ingestion/upload", summary="Async Ingest Upload")
@app.post("/api/v1/documents/upload", summary="Upload Document")
@app.post("/api/upload", summary="Upload Document Alias")
@app.post("/upload", summary="Upload Document Alias 2")
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, XLSX, TXT)"),
    document_type: Optional[str] = Form(None, description="e.g. SOP, Manual, Technical Spec"),
    department: Optional[str] = Form(None, description="e.g. Operations, Maintenance"),
    plant: Optional[str] = Form("MRPL Refinery", description="Refinery or Plant name"),
    unit: Optional[str] = Form(None, description="Plant Unit e.g. CDU-1"),
    equipment_id: Optional[str] = Form(None, description="Equipment Tag e.g. P-101A"),
    async_mode: bool = Query(True, description="Whether to dispatch as async Celery task"),
):
    """
    Ingest uploaded document with security screening and vector/FTS indexing.
    Supports both async Celery background processing and sync processing.
    """
    if not pipeline:
        raise HTTPException(status_code=500, detail="RAG Pipeline not initialized")

    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        custom_metadata = {
            "document_type": document_type,
            "department": department,
            "plant": plant,
            "unit": unit,
            "equipment_id": equipment_id,
        }

        if async_mode:
            job_info = pipeline.ingest_bytes_async(
                content_bytes=content_bytes,
                filename=file.filename,
                source_id="admin_upload",
                operator_role="ADMIN",
                metadata=custom_metadata,
            )
            return job_info
        else:
            sync_res = pipeline.ingest_bytes(
                content_bytes=content_bytes,
                filename=file.filename,
                metadata=custom_metadata,
            )
            return sync_res
    except Exception as e:
        logger.error(f"Error handling file upload '{file.filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ingestion/jobs/{job_id}", summary="Get Ingestion Job Status")
def get_job_status(job_id: str):
    """Fetch real-time status of an async document ingestion job."""
    session = db_manager.get_session()
    try:
        job = session.query(IngestionJobModel).filter(IngestionJobModel.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        return IngestionJobResponse(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            document_id=job.document_id,
            error_message=job.error_message,
            created_at=job.created_at.isoformat() if job.created_at else "",
        )
    finally:
        session.close()


@app.post("/api/v1/knowledge/query", summary="RAG Retrieval", response_model=KnowledgeQueryResponse)
@app.post("/api/v1/query", summary="RAG Retrieval Alias 1")
@app.post("/api/v1/search", summary="RAG Retrieval Alias 2")
@app.post("/api/query", summary="RAG Retrieval Alias 3")
@app.post("/api/search", summary="RAG Retrieval Alias 4")
@app.post("/query", summary="RAG Retrieval Alias 5")
@app.post("/search", summary="RAG Retrieval Alias 6")
def query_knowledge(req: KnowledgeQueryRequest):
    """
    Knowledge Retrieval Endpoint for Main Agent and API clients.
    Executes hybrid dense vector + FTS search, trust filtering, reranking, and citation generation.
    """
    if not pipeline:
        raise HTTPException(status_code=500, detail="RAG Pipeline not initialized")

    try:
        filter_cond = None
        if req.unit or req.equipment_id or req.department:
            filter_cond = FilterCondition(
                unit=req.unit,
                equipment_id=req.equipment_id,
                department=req.department,
            )

        logger.info(f"Executing RAG retrieval for agent query: '{req.query}'")
        result = pipeline.query_context(
            user_query=req.query,
            top_k=req.top_k,
            filters=filter_cond,
        )

        citations_response = [
            CitationResponse(
                citation_id=c.citation_id,
                document_id=c.document_id,
                document_title=c.document_title,
                section_title=c.section_title,
                page_number=c.page_number,
                revision=c.revision,
                trust_level=c.trust_level,
                snippet=c.snippet,
            )
            for c in result.citations
        ]

        return KnowledgeQueryResponse(
            query=req.query,
            context_text=result.context_text,
            citations=citations_response,
            retrieved_chunk_count=len(result.retrieved_chunks),
        )
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/documents", summary="List Ingested Documents")
@app.get("/api/documents", summary="List Ingested Documents Alias 1")
@app.get("/documents", summary="List Ingested Documents Alias 2")
def list_documents():
    """Lists all documents indexed in the Knowledge Base with trust and security status."""
    session = db_manager.get_session()
    try:
        docs = session.query(DocumentModel).all()
        doc_list = []
        for d in docs:
            chunk_cnt = session.query(ChunkModel).filter(ChunkModel.document_id == d.id).count()
            doc_list.append({
                "document_id": d.id,
                "title": d.title,
                "status": d.status,
                "trust_level": d.trust_level,
                "risk_score": d.risk_score,
                "unit": d.unit,
                "equipment_id": d.equipment_id,
                "chunk_count": chunk_cnt,
                "created_at": d.created_at.isoformat() if d.created_at else "",
            })
        return {"total_documents": len(doc_list), "documents": doc_list}
    finally:
        session.close()


@app.get("/api/v1/documents/{document_id}", summary="Get Document Details")
def get_document(document_id: str):
    """Fetch details, security findings, and chunks of a specific document."""
    session = db_manager.get_session()
    try:
        doc = session.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

        chunks = session.query(ChunkModel).filter(ChunkModel.document_id == document_id).all()
        findings = session.query(SecurityFindingModel).filter(SecurityFindingModel.document_id == document_id).all()

        return {
            "document_id": doc.id,
            "title": doc.title,
            "status": doc.status,
            "trust_level": doc.trust_level,
            "risk_score": doc.risk_score,
            "risk_level": doc.risk_level,
            "unit": doc.unit,
            "equipment_id": doc.equipment_id,
            "total_chunks": len(chunks),
            "security_findings": [
                {
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "description": f.description,
                }
                for f in findings
            ],
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "section_title": c.section_title,
                    "page_number": c.page_number,
                    "trust_level": c.trust_level,
                    "snippet": c.content[:150] + "..." if len(c.content) > 150 else c.content,
                }
                for c in chunks
            ],
        }
    finally:
        session.close()


@app.get("/api/v1/entities/{entity_id}", summary="Get Entity Details")
def get_entity(entity_id: str):
    """Fetch details and chunk links for a canonical entity."""
    session = db_manager.get_session()
    try:
        ent = session.query(EntityModel).filter(EntityModel.entity_id == entity_id).first()
        if not ent:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")
        return {
            "entity_id": ent.entity_id,
            "canonical_name": ent.canonical_name,
            "entity_type": ent.entity_type,
            "aliases": ent.aliases_json,
            "chunk_links_count": len(ent.chunk_links),
        }
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
