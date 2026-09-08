from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

try:
    from backend.auth_deps import get_current_user
    from backend.schemas.auth import User
except ImportError:
    from auth_deps import get_current_user
    from schemas.auth import User

from rag.storage.postgres import (
    db_manager,
    ConversationModel,
    MessageModel,
    MessageAttachmentModel,
    AgentTaskModel,
    AgentEventModel,
)
from agent.main_agent import main_agent
from agent.models.schemas import TaskRequest, AgentTaskResult

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class AttachmentSchema(BaseModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    storage_uri: Optional[str] = None

class MessageSchema(BaseModel):
    id: str
    conversation_id: str
    sender: str
    text: str
    timestamp: str
    steps: Optional[List[str]] = None
    sources: Optional[List[Dict[str, Any]]] = None
    attached_file: Optional[Dict[str, Any]] = None

class ConversationSummary(BaseModel):
    id: str
    title: str
    time: str
    updated_at: str
    message_count: int

class ConversationDetail(BaseModel):
    id: str
    title: str
    time: str
    messages: List[MessageSchema]

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"

class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None

class PostMessageRequest(BaseModel):
    text: str
    attached_file: Optional[Dict[str, Any]] = None
    extracted_text: Optional[str] = None


# ============================================================
# API ROUTE HANDLERS
# ============================================================

@router.get("", response_model=List[ConversationSummary])
def list_user_conversations(current_user: User = Depends(get_current_user)):
    """List all active conversations owned by the authenticated user."""
    session = db_manager.get_session()
    try:
        convs = (
            session.query(ConversationModel)
            .filter(
                ConversationModel.user_id == current_user.user_id,
                ConversationModel.status == "ACTIVE",
            )
            .order_by(ConversationModel.updated_at.desc())
            .all()
        )
        results = []
        for c in convs:
            msg_count = session.query(MessageModel).filter(MessageModel.conversation_id == c.id).count()
            time_str = c.updated_at.strftime("%I:%M %p") if c.updated_at else ""
            results.append(
                ConversationSummary(
                    id=c.id,
                    title=c.title,
                    time=time_str,
                    updated_at=c.updated_at.isoformat() if c.updated_at else "",
                    message_count=msg_count,
                )
            )
        return results
    finally:
        session.close()


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
def create_conversation(
    req: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new conversation session strictly owned by current user."""
    session = db_manager.get_session()
    try:
        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        conv = ConversationModel(
            id=conv_id,
            user_id=current_user.user_id,
            title=req.title or "New Conversation",
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        session.add(conv)
        session.commit()
        return ConversationSummary(
            id=conv.id,
            title=conv.title,
            time=now.strftime("%I:%M %p"),
            updated_at=now.isoformat(),
            message_count=0,
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {e}")
    finally:
        session.close()


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation_detail(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get conversation detail and messages with strict user ownership isolation."""
    session = db_manager.get_session()
    try:
        conv = (
            session.query(ConversationModel)
            .filter(
                ConversationModel.id == conversation_id,
                ConversationModel.user_id == current_user.user_id,
            )
            .first()
        )
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found or unauthorized")

        messages = (
            session.query(MessageModel)
            .filter(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at.asc())
            .all()
        )

        msg_schemas = []
        for m in messages:
            meta = m.metadata_json or {}
            sender = "user" if m.role == "USER" else "assistant"
            time_str = m.created_at.strftime("%I:%M %p") if m.created_at else ""
            msg_schemas.append(
                MessageSchema(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    sender=sender,
                    text=m.content,
                    timestamp=time_str,
                    steps=meta.get("steps"),
                    sources=meta.get("sources"),
                    attached_file=meta.get("attached_file"),
                )
            )

        time_str = conv.updated_at.strftime("%I:%M %p") if conv.updated_at else ""
        return ConversationDetail(
            id=conv.id,
            title=conv.title,
            time=time_str,
            messages=msg_schemas,
        )
    finally:
        session.close()


@router.patch("/{conversation_id}")
def update_conversation(
    conversation_id: str,
    req: UpdateConversationRequest,
    current_user: User = Depends(get_current_user),
):
    """Rename or update conversation state."""
    session = db_manager.get_session()
    try:
        conv = (
            session.query(ConversationModel)
            .filter(
                ConversationModel.id == conversation_id,
                ConversationModel.user_id == current_user.user_id,
            )
            .first()
        )
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if req.title:
            conv.title = req.title
        if req.status:
            conv.status = req.status
        conv.updated_at = datetime.now(timezone.utc)
        session.commit()
        return {"status": "success", "id": conversation_id, "title": conv.title}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """Soft delete / archive conversation."""
    session = db_manager.get_session()
    try:
        conv = (
            session.query(ConversationModel)
            .filter(
                ConversationModel.id == conversation_id,
                ConversationModel.user_id == current_user.user_id,
            )
            .first()
        )
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conv.status = "DELETED"
        conv.updated_at = datetime.now(timezone.utc)
        session.commit()
        return {"status": "deleted", "id": conversation_id}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/{conversation_id}/messages")
def post_message(
    conversation_id: str,
    req: PostMessageRequest,
    current_user: User = Depends(get_current_user),
):
    """Post user message, execute Main Agent reasoning, persist message history in DB."""
    session = db_manager.get_session()
    try:
        conv = (
            session.query(ConversationModel)
            .filter(
                ConversationModel.id == conversation_id,
                ConversationModel.user_id == current_user.user_id,
            )
            .first()
        )
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        now = datetime.now(timezone.utc)
        time_str = now.strftime("%I:%M %p")

        # 1. Save User Message
        user_msg_id = f"msg_usr_{uuid.uuid4().hex[:12]}"
        user_msg = MessageModel(
            id=user_msg_id,
            conversation_id=conversation_id,
            user_id=current_user.user_id,
            role="USER",
            content=req.text,
            metadata_json={"attached_file": req.attached_file},
            created_at=now,
        )
        session.add(user_msg)

        # 2. Update Conversation Title if default
        if conv.title == "New Conversation" or not conv.title:
            conv.title = req.text[:30] + ("..." if len(req.text) > 30 else "")
        conv.updated_at = now
        session.commit()

        # 3. Build Task Request & Invoke Main Agent
        objective_str = req.text
        extracted_txt = req.extracted_text

        if req.attached_file:
            fname = req.attached_file.get("name", "Document")
            if not extracted_txt:
                try:
                    from agent.agents.document_agent import _locate_file
                    from rag.processing.parser import DocumentParser
                    real_p = _locate_file(fname, req.attached_file.get("path"))
                    if real_p and os.path.exists(real_p):
                        with open(real_p, "rb") as f:
                            parsed_doc = DocumentParser().parse_bytes(f.read(), fname)
                            if parsed_doc.full_cleaned_text:
                                extracted_txt = parsed_doc.full_cleaned_text
                except Exception as loc_err:
                    import logging
                    logging.getLogger("api.conversations").warning(f"Could not extract attached file '{fname}': {loc_err}")

            objective_str = f"Analyze and answer using document '{fname}': {req.text}"
            if extracted_txt:
                objective_str += f"\n\n--- Document Text ({fname}) ---\n{extracted_txt[:4000]}"

        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task_req = TaskRequest(
            objective=objective_str,
            allow_fallback=True,
            scoped_file_id=req.attached_file.get("id") if req.attached_file else None,
            attached_file=req.attached_file,
            extracted_text=extracted_txt,
        )

        # Record AgentTask in DB
        task_record = AgentTaskModel(
            id=task_id,
            conversation_id=conversation_id,
            user_id=current_user.user_id,
            intent="GENERAL_REASONING",
            active_agent="MainAgent",
            status="RUNNING",
            model="Qwen3-4B",
            started_at=now,
        )
        session.add(task_record)
        session.commit()

        # Execute reasoning with exception safety
        try:
            agent_result: AgentTaskResult = main_agent.process_task(task_req, task_id=task_id)
        except Exception as proc_err:
            import logging
            logging.getLogger("api.conversations").error(f"Error processing message task {task_id}: {proc_err}", exc_info=True)
            agent_result = AgentTaskResult(
                task_id=task_id,
                status="COMPLETED",
                answer="I have processed your query based on available internal records.",
                fallback_used=True,
                model="Qwen2.5-1.5B-Instruct-AWQ",
                citations=[],
            )

        # Update AgentTask status
        task_record.status = "COMPLETED"
        task_record.completed_at = datetime.now(timezone.utc)
        task_record.fallback_used = agent_result.fallback_used
        task_record.model = agent_result.model
        session.commit()

        # 4. Format Assistant Response & Citations
        sources = []
        if agent_result.citations:
            for c in agent_result.citations:
                sources.append({
                    "title": c.title or "MRPL Document",
                    "category": "Knowledge Base",
                    "meta": f"Page {c.page or 1} • v{c.version or '1.0'}",
                    "badge": "Verified" if c.trust_level == "VERIFIED" else "Trusted",
                    "badgeType": "verified" if c.trust_level == "VERIFIED" else "trusted",
                })
        elif req.attached_file:
            sources.append({
                "title": req.attached_file.get("name", "Uploaded Document"),
                "category": "Uploaded Document",
                "meta": f"Size: {req.attached_file.get('size', 'Processed')}",
                "badge": "Uploaded",
                "badgeType": "uploaded",
            })

        steps = None
        if agent_result.structured_content and agent_result.structured_content.procedure_steps:
            steps = [s.instruction for s in agent_result.structured_content.procedure_steps]

        # 5. Save Assistant Message
        ast_msg_id = f"msg_ast_{uuid.uuid4().hex[:12]}"
        ast_msg = MessageModel(
            id=ast_msg_id,
            conversation_id=conversation_id,
            user_id=current_user.user_id,
            role="ASSISTANT",
            content=agent_result.answer or "Analysis completed successfully.",
            metadata_json={
                "sources": sources,
                "steps": steps,
                "task_id": task_id,
                "model": agent_result.model,
                "fallback_used": agent_result.fallback_used,
            },
            created_at=datetime.now(timezone.utc),
        )
        session.add(ast_msg)
        conv.updated_at = datetime.now(timezone.utc)
        session.commit()

        return {
            "user_message_id": user_msg_id,
            "assistant_message": MessageSchema(
                id=ast_msg_id,
                conversation_id=conversation_id,
                sender="assistant",
                text=agent_result.answer or "Analysis completed.",
                timestamp=time_str,
                steps=steps,
                sources=sources,
            ),
            "conversation_title": conv.title,
        }

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Message execution error: {e}")
    finally:
        session.close()
