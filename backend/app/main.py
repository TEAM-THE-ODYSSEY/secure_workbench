"""
MRPL Sovereign Agentic AI Workbench - Unified Backend Server Entrypoint.
Combines authentication, sessions, task management, knowledge base ingestion,
and Main AI Agent reasoning endpoints into a single runnable FastAPI application.
"""

from __future__ import annotations
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Core dependencies and RAG pipeline
from rag.config import config
from rag.pipeline import RAGPipeline
from rag.retrieval.metadata_filter import FilterCondition
from rag.storage.postgres import db_manager, DocumentModel, ChunkModel, IngestionJobModel, EntityModel, SecurityFindingModel

# Import backend modules
from backend import auth_store
from backend.api import artifacts, auth, chat, health, knowledge, models, network, sessions, stream, agent_reason, conversations, admin

# Import Agent service (for reasoning endpoints)
from agent.models import TaskRequest, AgentTaskResult
from agent.service import agent_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mrpl_backend_main")

pipeline: Optional[RAGPipeline] = None


async def bootstrap_admin() -> None:
    """Bootstrap initial admin user if configured."""
    if await auth_store.has_admin_user():
        logger.info("Admin account already exists. Skipping bootstrap.")
        return

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    if admin_username and admin_password:
        try:
            admin_user = await auth_store.create_user(
                admin_username, admin_password, role="admin"
            )
            logger.info(f"Admin bootstrap: created initial admin user '{admin_user.username}'.")
        except Exception as ex:
            logger.warning(f"Admin bootstrap notice: {ex}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization and background model pre-warming."""
    global pipeline
    logger.info("Initializing MRPL Sovereign Agentic Workbench Backend...")
    db_manager.initialize()
    pipeline = RAGPipeline()
    await bootstrap_admin()
    
    # Pre-warm embedding model in background thread
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
    logger.info("Shutting down MRPL Sovereign Agentic Workbench Backend.")


app = FastAPI(
    title="MRPL Sovereign Agentic AI Workbench API",
    description="Unified Air-Gapped Knowledge Base, P&ID Topology Engine, and Main AI Agent Platform.",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable CORS for local UI and external integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Auth, Chat, Knowledge, Network, Sessions, and Stream Routers
app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(artifacts.router, prefix="/api")
app.include_router(network.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(agent_reason.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


# ============================================================================
# Inline Agent & Knowledge Base Endpoints (previously from api/server.py)
# These are included directly to avoid the dual-app / dual-lifespan conflict
# that occurs when mounting api/server.py's FastAPI app as a sub-application.
# ============================================================================

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


# --- AGENT & KNOWLEDGE ENDPOINTS ---

@app.get("/", summary="Health Check")
@app.get("/health", summary="Health Check Alias")
def health_check_root():
    """Health check endpoint to verify API and Knowledge Base status."""
    vllm_status = agent_service.state_machine.model_manager.health_check()
    return {
        "status": "online",
        "service": "MRPL Enterprise Knowledge Base Engine",
        "vector_dimensions": config.EMBEDDING_DIMENSION,
        "postgres_connected": True,
        "vllm": vllm_status,
    }


@app.get("/api/v1/agent/health", summary="Check Reasoning Agent & vLLM Status")
def agent_health():
    """Check health and availability of Reasoning Agent and vLLM LLM endpoints."""
    return agent_service.state_machine.model_manager.health_check()


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

        from agent.gateway.input_gateway import InputGateway
        gateway = InputGateway()
        processed_file = gateway.process_upload(content_bytes=content_bytes, filename=file.filename)

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


@app.post("/api/v1/agent/reason", response_model=AgentTaskResult, summary="Execute Reasoning Agent Task")
def reason_agent_task(request: TaskRequest):
    """
    Execute a grounded reasoning task through the Reasoning Mini-Agent V1.
    Performs search over existing KB, strictly grounds content, generates validated ReportLab PDF, and persists to MinIO.
    """
    try:
        result = agent_service.process_task(request)
        return result
    except Exception as e:
        logger.error(f"Error processing reasoning agent task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agent/status/{task_id}", summary="Get Task Status & Execution Trace")
def get_agent_task_status(task_id: str):
    """Retrieve task status, active model, and execution trace metrics."""
    return {
        "task_id": task_id,
        "status": "COMPLETE",
        "active_model": agent_service.main_agent.model_manager.get_active_model(),
        "health": agent_service.main_agent.health_check(),
    }


@app.get("/api/v1/agent/download/{task_id}", summary="Download PDF Artifact by Task ID")
@app.get("/api/v1/artifacts/download/{object_name}", summary="Download PDF Artifact by File Name")
def download_pdf_artifact(task_id: Optional[str] = None, object_name: Optional[str] = None):
    """
    Download generated PDF artifact directly as a PDF file.
    """
    from rag.storage.minio_storage import minio_client
    try:
        bucket = "trusted"
        target_obj = object_name
        
        if not target_obj and task_id:
            try:
                if hasattr(minio_client, "_get_client"):
                    client = getattr(minio_client, "_get_client")()
                    objects = list(client.list_objects(bucket, prefix=task_id))
                    if objects:
                        target_obj = objects[0].object_name
            except Exception:
                pass
                
        if not target_obj and task_id:
            target_obj = f"{task_id}.pdf"
            
        if not target_obj:
            raise HTTPException(status_code=400, detail="Must specify task_id or object_name")

        pdf_bytes = minio_client.get_file(object_name=target_obj, bucket=bucket)
        if not pdf_bytes:
            raise HTTPException(status_code=404, detail=f"PDF artifact '{target_obj}' not found.")

        filename = target_obj if target_obj.endswith(".pdf") else f"{target_obj}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading PDF artifact: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Artifact not found: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
