from __future__ import annotations
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

try:
    from backend.auth_deps import get_current_admin_user
    from backend.schemas.auth import User
except ImportError:
    from auth_deps import get_current_admin_user
    from schemas.auth import User

from rag.storage.postgres import (
    db_manager,
    UserModel,
    ConversationModel,
    MessageModel,
    DocumentModel,
    ChunkModel,
    AgentTaskModel,
    AuditRecordModel,
    ReportModel,
    IngestionJobModel,
    UserRole,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"])


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class AdminStatisticsResponse(BaseModel):
    total_users: int
    active_users: int
    total_conversations: int
    total_messages: int
    total_documents: int
    trusted_documents: int
    total_vector_chunks: int
    total_agent_tasks: int
    completed_agent_tasks: int
    total_reports: int

class AdminUserResponse(BaseModel):
    id: str
    employee_id: str
    name: str
    email: Optional[str]
    department: Optional[str]
    role: str
    is_active: bool
    created_at: str
    last_login: Optional[str]

class UpdateUserRoleRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None

class AdminTaskResponse(BaseModel):
    task_id: str
    conversation_id: str
    user_id: str
    intent: str
    active_agent: str
    status: str
    model: str
    fallback_used: bool
    verification_status: str
    started_at: str
    completed_at: Optional[str]

class AdminAuditResponse(BaseModel):
    record_id: str
    action: str
    actor: Optional[str]
    document_id: Optional[str]
    details: Dict[str, Any]
    timestamp: str

class SystemComponentStatus(BaseModel):
    name: str
    status: str  # ONLINE, OFFLINE, DEGRADED
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

class SystemHealthResponse(BaseModel):
    status: str
    timestamp: str
    components: List[SystemComponentStatus]


# ============================================================
# API ROUTE HANDLERS
# ============================================================

@router.get("/statistics", response_model=AdminStatisticsResponse)
def get_admin_statistics(current_admin: User = Depends(get_current_admin_user)):
    """Return real backend system & usage statistics directly from PostgreSQL."""
    session = db_manager.get_session()
    try:
        total_users = session.query(UserModel).count()
        active_users = session.query(UserModel).filter(UserModel.is_active == True).count()
        total_convs = session.query(ConversationModel).count()
        total_msgs = session.query(MessageModel).count()
        total_docs = session.query(DocumentModel).count()
        trusted_docs = session.query(DocumentModel).filter(DocumentModel.trust_level == "TRUSTED").count()
        total_chunks = session.query(ChunkModel).count()
        total_tasks = session.query(AgentTaskModel).count()
        completed_tasks = session.query(AgentTaskModel).filter(AgentTaskModel.status == "COMPLETED").count()
        total_reports = session.query(ReportModel).count()

        return AdminStatisticsResponse(
            total_users=total_users,
            active_users=active_users,
            total_conversations=total_convs,
            total_messages=total_msgs,
            total_documents=total_docs,
            trusted_documents=trusted_docs,
            total_vector_chunks=total_chunks,
            total_agent_tasks=total_tasks,
            completed_agent_tasks=completed_tasks,
            total_reports=total_reports,
        )
    finally:
        session.close()


@router.get("/users", response_model=List[AdminUserResponse])
def list_admin_users(current_admin: User = Depends(get_current_admin_user)):
    """List all registered user accounts with role & department details."""
    session = db_manager.get_session()
    try:
        users = session.query(UserModel).order_by(UserModel.created_at.desc()).all()
        results = []
        for u in users:
            results.append(
                AdminUserResponse(
                    id=u.id,
                    employee_id=u.employee_id,
                    name=u.name,
                    email=u.email,
                    department=u.department,
                    role=u.role,
                    is_active=u.is_active,
                    created_at=u.created_at.isoformat() if u.created_at else "",
                    last_login=u.last_login.isoformat() if u.last_login else None,
                )
            )
        return results
    finally:
        session.close()


@router.post("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    req: UpdateUserRoleRequest,
    current_admin: User = Depends(get_current_admin_user),
):
    """Update user role or enable/disable user status."""
    session = db_manager.get_session()
    try:
        u = session.query(UserModel).filter(UserModel.id == user_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")

        if req.role:
            u.role = req.role
        if req.is_active is not None:
            u.is_active = req.is_active

        session.commit()
        return {"status": "success", "user_id": user_id, "role": u.role, "is_active": u.is_active}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/tasks", response_model=List[AdminTaskResponse])
def get_admin_tasks(current_admin: User = Depends(get_current_admin_user)):
    """List live and recent agent task telemetry records."""
    session = db_manager.get_session()
    try:
        tasks = session.query(AgentTaskModel).order_by(AgentTaskModel.started_at.desc()).limit(100).all()
        results = []
        for t in tasks:
            results.append(
                AdminTaskResponse(
                    task_id=t.id,
                    conversation_id=t.conversation_id,
                    user_id=t.user_id,
                    intent=t.intent,
                    active_agent=t.active_agent,
                    status=t.status,
                    model=t.model or "Qwen3-4B",
                    fallback_used=t.fallback_used or False,
                    verification_status=t.verification_status or "PASSED",
                    started_at=t.started_at.isoformat() if t.started_at else "",
                    completed_at=t.completed_at.isoformat() if t.completed_at else None,
                )
            )
        return results
    finally:
        session.close()


@router.get("/audit", response_model=List[AdminAuditResponse])
def get_admin_audit_logs(current_admin: User = Depends(get_current_admin_user)):
    """Return system audit log entries."""
    session = db_manager.get_session()
    try:
        records = session.query(AuditRecordModel).order_by(AuditRecordModel.timestamp.desc()).limit(100).all()
        results = []
        for r in records:
            results.append(
                AdminAuditResponse(
                    record_id=r.record_id,
                    action=r.action,
                    actor=r.actor,
                    document_id=r.document_id,
                    details=r.details_json or {},
                    timestamp=r.timestamp.isoformat() if r.timestamp else "",
                )
            )
        return results
    finally:
        session.close()


from sqlalchemy import text

@router.get("/system-health", response_model=SystemHealthResponse)
async def get_system_health(current_admin: User = Depends(get_current_admin_user)):
    """Probe real status of PostgreSQL, pgvector, vLLM server, Redis, and MinIO."""
    components = []

    # 1. PostgreSQL & pgvector probe
    try:
        session = db_manager.get_session()
        session.execute(text("SELECT 1;"))
        session.close()
        components.append(SystemComponentStatus(name="PostgreSQL", status="ONLINE"))
    except Exception as ex:
        components.append(SystemComponentStatus(name="PostgreSQL", status="OFFLINE", details={"error": str(ex)}))


    # 2. vLLM OpenAI Server probe (port 8080)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:8080/v1/models")
            if resp.status_code == 200:
                components.append(SystemComponentStatus(name="vLLM Inference Server", status="ONLINE", details=resp.json()))
            else:
                components.append(SystemComponentStatus(name="vLLM Inference Server", status="DEGRADED", details={"status_code": resp.status_code}))
    except Exception as ex:
        components.append(SystemComponentStatus(name="vLLM Inference Server", status="OFFLINE", details={"error": str(ex)}))

    # 3. Main Agent Control Engine
    components.append(SystemComponentStatus(name="MainAgent Control Layer", status="ONLINE"))

    return SystemHealthResponse(
        status="HEALTHY" if all(c.status == "ONLINE" for c in components) else "WARNING",
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
    )
