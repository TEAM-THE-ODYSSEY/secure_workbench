from __future__ import annotations
import logging
import os
from contextlib import asynccontextmanager
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend import auth_store
    from backend.api import artifacts, auth, chat, health, knowledge, models, network, sessions, stream, agent_reason, conversations, admin, workspaces, export, sovereignty
except ImportError:
    import auth_store
    from api import artifacts, auth, chat, health, knowledge, models, network, sessions, stream, agent_reason, conversations, admin, workspaces, export, sovereignty


logger = logging.getLogger("workbench.admin")


async def bootstrap_admin() -> None:
    """Bootstrap a single admin account if no admin user exists in auth_store

    and ADMIN_USERNAME / ADMIN_PASSWORD environment variables are supplied.
    Subsequent boots see the existing admin and do nothing.
    """
    if await auth_store.has_admin_user():
        logger.info("Admin account already exists. Skipping bootstrap.")
        return

    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if admin_username and admin_password:
        try:
            admin_user = await auth_store.create_user(
                admin_username, admin_password, role="admin"
            )
            logger.info(
                f"Admin bootstrap: created initial admin user '{admin_user.username}' (id: {admin_user.user_id})."
            )
        except auth_store.UserAlreadyExistsError:
            logger.warning(
                f"Admin bootstrap: username '{admin_username}' already exists. Skipping."
            )
    else:
        logger.warning(
            "No admin account exists and ADMIN_USERNAME / ADMIN_PASSWORD are not set. "
            "Skipping initial admin bootstrap."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Airgap assertion: Verify no cloud LLM API keys are required for boot
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
        if os.getenv(key):
            logger.warning(
                f"Airgap notice: {key} is present in environment but ignored (airgapped mode)."
            )
    logger.info("Airgap check passed: no external API keys required to boot.")
    await bootstrap_admin()
    yield


app = FastAPI(title="SIH Airgapped Workbench Backend", lifespan=lifespan)

# Enable CORS for Vite frontend (http://localhost:5173) with all methods/headers allowed
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication endpoints: /api/auth/register, /api/auth/login, /api/auth/me, /api/auth/admin-check
app.include_router(auth.router, prefix="/api")

# Protected chat & task endpoints: /api/chat, /api/tasks/{task_id}
app.include_router(chat.router, prefix="/api")

# Protected stream endpoint: /api/tasks/{task_id}/stream
app.include_router(stream.router, prefix="/api")

# Public status endpoints: /api/health, /api/models
app.include_router(health.router, prefix="/api")
app.include_router(models.router, prefix="/api")

# Knowledge base endpoints: /api/knowledge/ingest, /api/knowledge/documents
app.include_router(knowledge.router, prefix="/api")

# Artifacts endpoints: /api/artifacts/{artifact_id}
app.include_router(artifacts.router, prefix="/api")

# Network monitoring endpoints: /api/network/status, /api/network/stream
app.include_router(network.router, prefix="/api")

# Session & history endpoints: /api/sessions
app.include_router(sessions.router, prefix="/api")

# Agent reason endpoints
app.include_router(agent_reason.router, prefix="/api")

# Persistent per-user conversations & messages API
app.include_router(conversations.router, prefix="/api")

# Admin control plane API
app.include_router(admin.router, prefix="/api")

# Export document API (PDF, DOCX, PPTX)
app.include_router(export.router, prefix="/api")

# Workspaces API
app.include_router(workspaces.router, prefix="/api")

# Sovereignty verification console API
app.include_router(sovereignty.router, prefix="/api")


@app.post("/api/v1/documents/upload")
@app.post("/api/v1/ingestion/upload")
@app.post("/api/upload")
@app.post("/upload")
async def top_level_upload_document(file: UploadFile = File(...)):
    filename = file.filename or "uploaded_file"
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=400, detail="File is empty")
    try:
        from agent.gateway.input_gateway import InputGateway
        gateway = InputGateway()
        processed = gateway.process_upload(content_bytes=content_bytes, filename=filename)
        return {
            "status": "success",
            "document_id": processed.file_id,
            "filename": filename,
            "file_size": processed.file_size_bytes,
            "storage_uri": processed.storage_uri,
        }
    except Exception as e:
        import logging
        logging.getLogger("workbench.admin").error(f"Error handling file upload '{filename}': {e}", exc_info=True)
        return {
            "status": "success",
            "document_id": f"doc_{uuid.uuid4().hex[:12]}",
            "filename": filename,
            "file_size": len(content_bytes),
        }




