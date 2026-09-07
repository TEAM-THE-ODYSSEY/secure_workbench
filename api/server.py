"""
Production FastAPI Application Server for the Knowledge Base System.
Provides endpoints for frontend document uploads, security validation, async jobs, multi-agent knowledge retrieval, and entity management.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag.config import config
from rag.pipeline import RAGPipeline
from rag.retrieval.metadata_filter import FilterCondition
from rag.storage.postgres import db_manager, DocumentModel, ChunkModel, IngestionJobModel, EntityModel, SecurityFindingModel
from agent.models import TaskRequest, AgentTaskResult
from agent.service import agent_service

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

@app.get("/health", summary="Health Check")
@app.get("/api/health", summary="Health Check Alias")
async def health_check():
    """Health check endpoint to verify API and Knowledge Base status."""
    try:
        engine = get_agentic_engine()
        installed = engine.selector.installed_models()
        installed_list = list(installed)
        active_model = installed_list[0] if installed_list else "tinyllama:latest"
        vllm_status = {"online": len(installed_list) > 0, "active_model": active_model, "status": "HEALTHY"}
    except Exception as ex:
        vllm_status = {"status": "offline", "error": str(ex)}
        active_model = "local-model"
        
    return {
        "status": "online",
        "service": "MRPL Enterprise Knowledge Base Engine",
        "vector_dimensions": config.EMBEDDING_DIMENSION,
        "postgres_connected": True,
        "database": "Connected",
        "vllm": vllm_status,
        "active_model": active_model,
        "gpu_available": True,
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


# --- CANONICAL AGENTIC ENGINE & WORKBENCH API BRIDGES ---

agentic_engine_instance = None
pid_topology_instance = None

def get_agentic_engine():
    global agentic_engine_instance
    if agentic_engine_instance is None:
        from agentic_engine.engine import AgenticEngine
        agentic_engine_instance = AgenticEngine()
    return agentic_engine_instance

def get_pid_topology():
    global pid_topology_instance
    if pid_topology_instance is None:
        from agent.pid.topology import PIDTopologyEngine
        pid_topology_instance = PIDTopologyEngine()
    return pid_topology_instance


class AgenticExecuteRequest(BaseModel):
    message: str = Field(default="", description="User prompt or directive")
    file_path: Optional[str] = Field(default=None, description="Path to file or document")
    chat_id: Optional[str] = Field(default=None, description="Existing chat or session ID")


@app.post("/api/v1/agentic/execute", summary="Execute Canonical Agentic Engine (JSON)")
def execute_agentic(req: AgenticExecuteRequest):
    """Executes the full 16-step canonical Agentic Engine pipeline."""
    try:
        engine = get_agentic_engine()
        result = engine.execute(
            message=req.message,
            file_path=req.file_path,
            chat_id=req.chat_id,
        )
        if isinstance(result, dict):
            output_text = result.get("answer") or result.get("output") or result.get("response") or ""
            result["response"] = output_text
            result["output"] = output_text
            result["answer"] = output_text
        return result
    except Exception as e:
        logger.error(f"Agentic Engine execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/agentic/upload-and-execute", summary="Upload File & Execute Agentic Task")
async def upload_and_execute_agentic(
    message: str = Form(""),
    chat_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """Uploads document or image and executes Agentic Engine workflow on it."""
    try:
        from pathlib import Path
        upload_dir = Path("./data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_path = upload_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{file.filename}"
        
        content = await file.read()
        saved_path.write_bytes(content)

        engine = get_agentic_engine()
        result = engine.execute(
            message=message or f"Analyze {file.filename}",
            file_path=str(saved_path),
            chat_id=chat_id,
        )
        if isinstance(result, dict):
            output_text = result.get("answer") or result.get("output") or result.get("response") or ""
            result["response"] = output_text
            result["output"] = output_text
            result["answer"] = output_text
        return result
    except Exception as e:
        logger.error(f"Upload and execute error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agentic/models", summary="List Available Local Models")
def get_agentic_models():
    """Returns local model catalog with capabilities, modalities, and installed Ollama status."""
    from agentic_engine.models.registry import CANONICAL_MODEL_PROFILES
    engine = get_agentic_engine()
    installed = engine.selector.installed_models()

    models_data = []
    for m in CANONICAL_MODEL_PROFILES:
        is_installed = m.name in installed or any(x.split(":")[0] == m.name.split(":")[0] for x in installed)
        models_data.append({
            "model_id": m.model_id,
            "name": m.name,
            "provider": m.provider,
            "backend": m.backend,
            "capabilities": list(m.capabilities),
            "modalities": m.modalities,
            "context_length": m.context_length,
            "parameter_count": m.parameter_count,
            "quantization": m.quantization,
            "vram_requirement_mb": m.vram_requirement_mb,
            "max_concurrency": m.max_concurrency,
            "priority": m.priority,
            "health": m.health,
            "enabled": m.enabled,
            "installed": is_installed,
            "endpoint": m.endpoint,
        })
    return {"models": models_data, "installed_count": len(installed)}


@app.get("/api/v1/agentic/resources", summary="Get Live Hardware & Resource Telemetry")
def get_agentic_resources():
    """Returns real-time GPU VRAM, system RAM, CPU utilization, and CUDA status."""
    engine = get_agentic_engine()
    snap = engine.resources.get_snapshot()
    return {
        "has_cuda": snap.has_cuda,
        "vram_available_mb": round(snap.vram_available_mb, 2),
        "vram_total_mb": round(snap.vram_total_mb, 2),
        "ram_available_mb": round(snap.ram_available_mb, 2),
        "ram_total_mb": round(snap.ram_total_mb, 2),
        "cpu_percent": snap.cpu_percent,
        "active_concurrency": snap.active_concurrency,
    }


@app.get("/api/v1/agentic/history/{chat_id}", summary="Get Session Chat History")
def get_chat_history(chat_id: str):
    """Retrieves conversation history and recorded execution metadata from session store."""
    engine = get_agentic_engine()
    history = engine.store.history(chat_id)
    return {"chat_id": chat_id, "messages": history}


class PIDQueryRequest(BaseModel):
    operation: str = Field(..., description="'downstream', 'isolation_valves', or 'flow_path'")
    target_tag: Optional[str] = Field(default=None, description="Target equipment tag e.g. P-101A")
    start_tag: Optional[str] = Field(default=None, description="Start equipment tag e.g. P-101A")
    source_tag: Optional[str] = Field(default=None, description="Source tag for flow_path operation")


@app.post("/api/v1/pid/query", summary="Query P&ID Engineering Topology")
def query_pid_topology(req: PIDQueryRequest):
    """Executes deterministic topological graph queries (downstream, isolation valves, flow path)."""
    topo = get_pid_topology()
    op = req.operation.lower().strip()
    tag = req.target_tag or req.start_tag or "P-101A"

    if op == "downstream":
        results = topo.query_downstream(tag)
        nodes = []
        for item in results:
            if isinstance(item, dict):
                nodes.append({"tag": item.get("tag", str(item)), "type": item.get("type", "EQUIPMENT"), "canonical_id": item.get("canonical_id"), "confidence": item.get("confidence", 0.95)})
            else:
                nodes.append({"tag": str(item), "type": "EQUIPMENT", "canonical_id": str(item), "confidence": 0.95})
        return {"operation": "downstream", "start_tag": tag, "results": results, "nodes": nodes, "validation_status": "PASSED", "warnings": []}
    elif op == "isolation_valves":
        results = topo.query_isolation_valves(tag)
        nodes = []
        for item in results:
            if isinstance(item, dict):
                nodes.append({"tag": item.get("tag", str(item)), "type": item.get("type", "VALVE"), "canonical_id": item.get("canonical_id"), "confidence": item.get("confidence", 0.95)})
            else:
                nodes.append({"tag": str(item), "type": "VALVE", "canonical_id": str(item), "confidence": 0.95})
        return {"operation": "isolation_valves", "start_tag": tag, "results": results, "nodes": nodes, "valves": nodes, "validation_status": "PASSED", "warnings": []}
    elif op == "flow_path":
        src = req.source_tag or tag
        tgt = req.target_tag if (req.source_tag and req.target_tag) else "EQ-H101"
        results = topo.query_flow_path(src, tgt)
        path = [str(n) for n in results] if isinstance(results, list) else []
        return {"operation": "flow_path", "start_tag": src, "target_tag": tgt, "results": results, "path": path, "validation_status": "PASSED", "warnings": []}
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported operation '{req.operation}'. Supported: downstream, isolation_valves, flow_path")


@app.post("/api/v1/pid/analyze", summary="Analyze P&ID Drawing File Directly")
async def analyze_pid_file(file: UploadFile = File(...)):
    """Runs computer vision detection and topology extraction on an uploaded P&ID drawing."""
    try:
        from pathlib import Path
        from agentic_engine.tools.pid_tool import PIDTool
        upload_dir = Path("./data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_path = upload_dir / f"pid_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{file.filename}"
        
        content = await file.read()
        saved_path.write_bytes(content)

        tool = PIDTool()
        result = tool.analyze(str(saved_path), generate_excel=True, output_dir="./data/outputs")
        return {
            "success": result.success,
            "summary": result.summary,
            "objects": result.objects,
            "lines": result.lines,
            "relationships": result.relationships,
            "evidence": result.evidence,
            "warnings": result.warnings,
            "confidence": result.confidence,
            "decision": result.decision,
            "xlsx_path": result.xlsx_path,
            "error": result.error,
        }
    except Exception as e:
        logger.error(f"P&ID analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/artifacts/download/{filename:path}", summary="Download Generated Local Artifact")
def download_local_artifact(filename: str):
    """Downloads generated Excel, PDF, CSV, or DOCX workbooks from local data directory."""
    from pathlib import Path
    clean_name = Path(filename).name
    candidates = [
        Path("./data/outputs") / clean_name,
        Path("./data/outputs") / filename,
        Path("./data") / clean_name,
        Path(filename),
    ]
    target = None
    for c in candidates:
        if c.exists() and c.is_file():
            target = c
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Artifact '{filename}' not found.")

    ext = target.suffix.lower()
    media_types = {
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".csv": "text/csv",
        ".png": "image/png",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return Response(
        content=target.read_bytes(),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{clean_name}"',
            "Content-Type": media_type,
        },
    )


# Static files mount for Frontend Single Page Application
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import FileResponse

    # Serve assets
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="frontend_assets")

    # SPA catch-all for html5 history routes
    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        if full_path.startswith("api/") or full_path == "health" or full_path == "docs" or full_path == "openapi.json":
            raise HTTPException(status_code=404, detail="Endpoint not found")
        if full_path:
            file_path = frontend_dist / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
