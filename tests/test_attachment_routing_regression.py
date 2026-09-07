"""
Regression test suite for attachment referent resolution, RAG routing, EvidenceFusion, and LLM generation.
Covers all 7 mandatory regression scenarios:
1. Attachment + "explain it" => DOCUMENT_ANALYSIS => correct file_id => evidence_chunks > 0 => LLM called
2. Attachment + "summarize this document" => DOCUMENT_ANALYSIS
3. Attachment + "what does it say about PPE?" => targeted file retrieval
4. No attachment + "Explain crude oil refining" => GENERAL_KNOWLEDGE => no local KB retrieval
5. No attachment + MRPL-specific question => LOCAL_KNOWLEDGE
6. Attachment + "compare this with MRPL shutdown SOP" => DOCUMENT_ANALYSIS + LOCAL_KNOWLEDGE => EvidenceFusion combines both sources
7. Multiple attachments + "explain it" => ask user to identify the file
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.models.schemas import TaskRequest, TaskContext
from agent.orchestrator import main_orchestrator
from agent.models.model_manager import ModelManager


@pytest.fixture
def mock_attachment():
    return {
        "name": "Health And Safety.docx",
        "file_id": "doc_health_safety_001",
        "path": "/home/hinata/SIH2026/backend/workspace/knowledge_base/Health And Safety.docx",
    }


@pytest.fixture
def mock_attachments_multiple():
    return [
        {
            "name": "Health And Safety.docx",
            "file_id": "doc_health_safety_001",
        },
        {
            "name": "SOP-CDU-101.pdf",
            "file_id": "doc_sop_cdu_101",
        },
    ]


def test_1_attachment_explain_it(mock_attachment):
    """1. Attachment + 'explain it' => DOCUMENT_ANALYSIS => correct file_id => evidence_chunks > 0 => LLM called"""
    req = TaskRequest(
        objective="explain it",
        attached_file=mock_attachment,
    )
    result = main_orchestrator.process_task(req)

    assert result.status == "COMPLETE"
    assert result.answer is not None
    assert len(result.answer) > 20
    # Citations/evidence check
    assert len(result.citations) > 0
    assert any(c.document_id in ("doc_health_safety_001", "Health And Safety.docx") for c in result.citations)
    # Active model used
    assert result.model is not None


def test_2_attachment_summarize_this_document(mock_attachment):
    """2. Attachment + 'summarize this document' => DOCUMENT_ANALYSIS"""
    ctx = TaskContext(
        task_id="test_task_2",
        user_id="test_user",
        conversation_id="conv_002",
        query="summarize this document",
        attachments=[mock_attachment],
    )
    plan = main_orchestrator.build_task_plan(ctx)
    assert plan.intent == "DOCUMENT_ANALYSIS"
    assert any(a.name == "document" for a in plan.agents)


def test_3_attachment_targeted_ppe_retrieval(mock_attachment):
    """3. Attachment + 'what does it say about PPE?' => targeted file retrieval"""
    req = TaskRequest(
        objective="what does it say about PPE?",
        attached_file=mock_attachment,
    )
    result = main_orchestrator.process_task(req)

    assert result.status == "COMPLETE"
    assert len(result.citations) > 0
    assert result.answer is not None


def test_4_no_attachment_general_knowledge():
    """4. No attachment + 'Explain crude oil refining' => GENERAL_KNOWLEDGE => no local KB retrieval"""
    ctx = TaskContext(
        task_id="test_task_4",
        user_id="test_user",
        conversation_id="conv_004",
        query="Explain crude oil refining",
        attachments=[],
    )
    plan = main_orchestrator.build_task_plan(ctx)
    assert plan.intent == "GENERAL_KNOWLEDGE"
    assert not any(a.name == "knowledge" for a in plan.agents)

    req = TaskRequest(objective="Explain crude oil refining")
    result = main_orchestrator.process_task(req)
    assert result.status == "COMPLETE"
    assert result.answer is not None


def test_5_no_attachment_local_knowledge():
    """5. No attachment + MRPL-specific question => LOCAL_KNOWLEDGE"""
    ctx = TaskContext(
        task_id="test_task_5",
        user_id="test_user",
        conversation_id="conv_005",
        query="What is the shutdown SOP for CDU-1 at MRPL?",
        attachments=[],
    )
    plan = main_orchestrator.build_task_plan(ctx)
    assert plan.intent == "LOCAL_KNOWLEDGE"
    assert any(a.name == "knowledge" for a in plan.agents)


def test_6_attachment_compare_with_mrpl_sop(mock_attachment):
    """6. Attachment + 'compare this with MRPL shutdown SOP' => DOCUMENT_ANALYSIS + LOCAL_KNOWLEDGE => EvidenceFusion combines both sources"""
    ctx = TaskContext(
        task_id="test_task_6",
        user_id="test_user",
        conversation_id="conv_006",
        query="compare this with MRPL shutdown SOP",
        attachments=[mock_attachment],
    )
    plan = main_orchestrator.build_task_plan(ctx)
    assert plan.intent == "DOCUMENT_ANALYSIS"
    agent_names = [a.name for a in plan.agents]
    assert "document" in agent_names
    assert "knowledge" in agent_names

    req = TaskRequest(
        objective="compare this with MRPL shutdown SOP",
        attached_file=mock_attachment,
    )
    result = main_orchestrator.process_task(req)
    assert result.status == "COMPLETE"
    assert result.answer is not None


def test_7_multiple_attachments_explain_it(mock_attachments_multiple):
    """7. Multiple attachments + 'explain it' => ask user to identify the file"""
    req = TaskRequest(
        objective="explain it",
        attached_file=mock_attachments_multiple[0],
    )
    # Pass both attachments in TaskContext
    ctx = TaskContext(
        task_id="test_task_7",
        user_id="test_user",
        conversation_id="conv_007",
        query="explain it",
        attachments=mock_attachments_multiple,
    )
    plan = main_orchestrator.build_task_plan(ctx)
    assert plan.intent == "AMBIGUOUS_ATTACHMENTS"

    result = main_orchestrator.process_task(
        TaskRequest(objective="explain it", attachments=mock_attachments_multiple),
    )
    assert "Multiple attachments detected" in result.answer
    # Explicit check when attachments list has 2 files in context
    context_multi = TaskContext(
        task_id="test_task_7_exec",
        user_id="test_user",
        conversation_id="conv_007",
        query="explain it",
        attachments=mock_attachments_multiple,
    )
    res_multi = main_orchestrator.run_sync(context_multi)
    assert "Multiple attachments detected" in res_multi.answer
    assert "Health And Safety.docx" in res_multi.answer
    assert "SOP-CDU-101.pdf" in res_multi.answer
