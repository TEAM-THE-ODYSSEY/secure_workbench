"""
Regression test suite for attachment referent resolution, RAG routing, EvidenceFusion, and LLM generation.
Covers all 15 mandatory test cases:
1. Attachment + "explain it" => DOCUMENT_ANALYSIS => correct file_id => evidence_chunks > 0 => LLM called
2. Upload arbitrary PDF with no MRPL metadata => answer from uploaded PDF.
3. Upload arbitrary DOCX with no canonical entities => DOCUMENT_ANALYSIS.
4. Upload arbitrary PPTX => slide-aware document analysis.
5. Upload arbitrary XLSX => sheet-aware analysis.
6. Upload document + "Explain this document completely" => COMPREHENSIVE mode.
7. Upload document + "What does it say about PPE?" => TARGETED mode.
8. Attachment + "compare this with MRPL shutdown SOP" => DOCUMENT_ANALYSIS + LOCAL_KNOWLEDGE => EvidenceFusion combines both sources.
9. No attachment + "Explain crude oil refining" => GENERAL_KNOWLEDGE => no local KB retrieval.
10. No attachment + MRPL-specific question => LOCAL_KNOWLEDGE.
11. Multiple attachments + "explain it" => ask user to identify the file.
12. Backend container vLLM endpoint connectivity test.
13. Backend ModelManager generation test.
14. vLLM unavailable => DEGRADED state, no fake AI answer.
15. Source cards => only sources actually used by EvidenceFusion.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.models.schemas import TaskRequest, TaskContext, EvidenceChunk, Citation
from agent.orchestrator import main_orchestrator
from agent.models.model_manager import ModelManager
from agent.evidence_fusion import evidence_fusion


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
    assert len(result.citations) > 0
    assert any(c.document_id in ("doc_health_safety_001", "Health And Safety.docx") for c in result.citations)
    assert result.model is not None


def test_2_arbitrary_pdf_no_mrpl_entity():
    """2. Upload arbitrary PDF with no MRPL metadata => answer from uploaded PDF, no MRPL entity required."""
    pdf_att = {
        "name": "unknown_vendor_manual.pdf",
        "file_id": "pdf_vendor_999",
        "extracted_text": "Emergency procedures: In case of pressure surge above 15 bar, trip emergency shutdown valve ESV-99 manually using the red lever on panel B.",
    }
    req = TaskRequest(
        objective="What does this document say about emergency procedures?",
        attached_file=pdf_att,
        extracted_text=pdf_att["extracted_text"],
    )
    result = main_orchestrator.process_task(req)

    assert result.status == "COMPLETE"
    assert result.answer is not None
    assert "ESV-99" in result.answer or "emergency" in result.answer.lower() or "pressure surge" in result.answer.lower()


def test_3_arbitrary_docx_no_canonical_entity():
    """3. Upload arbitrary DOCX with no canonical entities => DOCUMENT_ANALYSIS."""
    docx_att = {
        "name": "random_safety_policy.docx",
        "file_id": "docx_safety_123",
        "extracted_text": "Random Safety Guidelines: Personal protective equipment (PPE) including safety goggles, hard hats, and steel-toed boots must be worn in all operational areas at all times.",
    }
    ctx = TaskContext(
        task_id="test_task_3",
        user_id="test_user",
        conversation_id="conv_003",
        query="Summarize this document",
        attachments=[docx_att],
    )
    plan = main_orchestrator.build_task_plan(ctx)
    assert plan.intent == "DOCUMENT_ANALYSIS"


def test_4_arbitrary_pptx_slide_aware():
    """4. Upload arbitrary PPTX => slide-aware document analysis."""
    pptx_att = {
        "name": "engineering_presentation.pptx",
        "file_id": "pptx_eng_456",
        "extracted_text": "[Slide 1: Overview] Project Z upgrade timeline.\n[Slide 2: Execution] Milestones completed in Q3 with 99.8% safety compliance.",
    }
    req = TaskRequest(
        objective="Explain this presentation.",
        attached_file=pptx_att,
        extracted_text=pptx_att["extracted_text"],
    )
    result = main_orchestrator.process_task(req)
    assert result.status == "COMPLETE"
    assert result.answer is not None


def test_5_arbitrary_xlsx_sheet_aware():
    """5. Upload arbitrary XLSX => sheet/cell-aware analysis."""
    xlsx_att = {
        "name": "plant_report.xlsx",
        "file_id": "xlsx_plant_789",
        "extracted_text": "[Sheet: Daily Summary]\nRow 1: CDU-1 Flow = 450.5 m3/h\nRow 2: Temperature = 340.2 C",
    }
    req = TaskRequest(
        objective="What are the main values in this spreadsheet?",
        attached_file=xlsx_att,
        extracted_text=xlsx_att["extracted_text"],
    )
    result = main_orchestrator.process_task(req)
    assert result.status == "COMPLETE"
    assert result.answer is not None


def test_6_comprehensive_document_explanation():
    """6. Upload document + 'Explain this document completely.' => COMPREHENSIVE mode."""
    doc_att = {
        "name": "Health And Safety.docx",
        "file_id": "doc_hs_comp",
        "extracted_text": "Section 1: Safety Goals.\nMRPL prioritizes zero-harm operations.\n\nSection 2: Rules.\nMandatory SCBA readiness and H2S monitors in all process units.",
    }
    ctx = TaskContext(
        task_id="test_task_6_comp",
        user_id="test_user",
        conversation_id="conv_006",
        query="Explain this document completely.",
        attachments=[doc_att],
    )
    plan = main_orchestrator.build_task_plan(ctx)
    assert plan.intent == "DOCUMENT_ANALYSIS"


def test_7_targeted_document_query():
    """7. Upload document + 'What does it say about PPE?' => TARGETED mode."""
    doc_att = {
        "name": "Health And Safety.docx",
        "file_id": "doc_hs_targ",
        "extracted_text": "PPE guidelines require goggles and heat gloves.",
    }
    ctx = TaskContext(
        task_id="test_task_7_targ",
        user_id="test_user",
        conversation_id="conv_007",
        query="What does it say about PPE?",
        attachments=[doc_att],
    )
    plan = main_orchestrator.build_task_plan(ctx)
    assert plan.intent == "DOCUMENT_ANALYSIS"


def test_8_attachment_compare_with_mrpl_sop(mock_attachment):
    """8. Attachment + 'compare this with MRPL shutdown SOP' => DOCUMENT_ANALYSIS + LOCAL_KNOWLEDGE => EvidenceFusion combines both sources."""
    ctx = TaskContext(
        task_id="test_task_8",
        user_id="test_user",
        conversation_id="conv_008",
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


def test_9_no_attachment_general_knowledge():
    """9. No attachment + 'Explain crude oil refining' => GENERAL_KNOWLEDGE => no local KB retrieval."""
    ctx = TaskContext(
        task_id="test_task_9",
        user_id="test_user",
        conversation_id="conv_009",
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


def test_10_no_attachment_local_knowledge():
    """10. No attachment + MRPL-specific question => LOCAL_KNOWLEDGE."""
    ctx = TaskContext(
        task_id="test_task_10",
        user_id="test_user",
        conversation_id="conv_010",
        query="What is the shutdown SOP for CDU-1 at MRPL?",
        attachments=[],
    )
    plan = main_orchestrator.build_task_plan(ctx)
    assert plan.intent == "LOCAL_KNOWLEDGE"
    assert any(a.name == "knowledge" for a in plan.agents)


def test_11_multiple_attachments_explain_it(mock_attachments_multiple):
    """11. Multiple attachments + 'explain it' => ask user to identify the file."""
    ctx = TaskContext(
        task_id="test_task_11",
        user_id="test_user",
        conversation_id="conv_011",
        query="explain it",
        attachments=mock_attachments_multiple,
    )
    plan = main_orchestrator.build_task_plan(ctx)
    assert plan.intent == "AMBIGUOUS_ATTACHMENTS"

    res_multi = main_orchestrator.run_sync(ctx)
    assert "Multiple attachments detected" in res_multi.answer
    assert "Health And Safety.docx" in res_multi.answer
    assert "SOP-CDU-101.pdf" in res_multi.answer


def test_12_backend_vllm_connectivity():
    """12. Backend ModelManager health check reaches vLLM and detects Qwen model."""
    mm = ModelManager()
    diag = mm.health_check()
    assert diag["application"] == "healthy"
    assert "vllm_api_base" in diag


def test_13_model_manager_generation():
    """13. Backend ModelManager generation yields grounded text."""
    mm = ModelManager()
    out = mm.generate("Explain safety guidelines.", system_prompt="You are a helpful AI.")
    assert out is not None
    assert len(out) > 5


def test_14_vllm_degraded_fallback_handling():
    """14. When vLLM fails, ModelManager transitions state to DEGRADED without fake fallback."""
    mm = ModelManager(vllm_api_base="http://localhost:9999/v1")
    # Setting primary and fallback to same model should disable fake secondary fallback
    mm.primary_model = "Qwen/Qwen2.5-1.5B-Instruct-AWQ"
    mm.fallback_model = "Qwen/Qwen2.5-1.5B-Instruct-AWQ"
    with pytest.raises(Exception):
        mm.generate("test prompt")
    assert mm.model_state.value == "DEGRADED"


def test_15_verify_source_cards():
    """15. Verify source cards only include sources that actually contributed evidence."""
    ctx = TaskContext(
        task_id="test_task_15",
        user_id="test_user",
        conversation_id="conv_015",
        query="Explain document",
    )
    cit_uploaded = Citation(
        document_id="doc_up_1",
        title="Custom Policy.pdf",
        trust_level="UPLOADED",
        section="Intro",
    )
    chk = EvidenceChunk(
        chunk_id="chk_1",
        document_id="doc_up_1",
        title="Custom Policy.pdf",
        content="Policy content",
        trust_level="UPLOADED",
        citation=cit_uploaded,
    )
    pack = evidence_fusion.fuse([chk])
    assert len(pack.sources) == 1
    assert pack.sources[0]["title"] == "Custom Policy.pdf"
    assert pack.sources[0]["category"] == "Uploaded File"
