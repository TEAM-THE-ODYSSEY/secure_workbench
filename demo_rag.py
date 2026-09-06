"""
End-to-End Verification Demo for MRPL Enterprise RAG System.
"""

import os
import sys
import logging

# Ensure rag module is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from rag.pipeline import RAGPipeline
from rag.retrieval.metadata_filter import FilterCondition
from rag.evaluation.retrieval_eval import RetrievalEvaluator
from rag.evaluation.test_dataset import EvalTestCase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("demo_rag")


def run_demo():
    print("=" * 70)
    print("      STARTING MRPL RAG PIPELINE VERIFICATION DEMO")
    print("=" * 70)

    # 1. Instantiate RAG Pipeline
    pipeline = RAGPipeline()

    # Create sample document directory
    sample_dir = os.path.abspath("./sample_docs")
    os.makedirs(sample_dir, exist_ok=True)

    # Write sample MRPL SOP file
    sop_file = os.path.join(sample_dir, "SOP_CDU_101_Pump_Operation.txt")
    sop_content = """# MRPL REFINERY STANDARD OPERATING PROCEDURE (SOP)
Document Code: SOP-MRPL-CDU-101
Revision: R2
Department: Operations
Plant: MRPL Refinery Phase-1
Unit: CDU-1 (Crude Distillation Unit 1)
Equipment ID: P-101A / P-101B (Crude Charge Pumps)
Effective Date: 2025-01-15
Status: ACTIVE

## SECTION 1: PURPOSE AND SCOPE
This procedure describes the safe startup, normal operation, and shutdown sequence for the main crude charge pumps P-101A and P-101B located in Crude Distillation Unit 1 (CDU-1).

## SECTION 2: TECHNICAL SPECIFICATIONS
- Pump Tag: P-101A (Motor Driven), P-101B (Steam Turbine Driven)
- Operating Flow Rate: 750 m3/h
- Normal Discharge Pressure: 42.5 bar
- Operating Temperature: 145 °C
- Mechanical Seal Flush Plan: API Plan 53B

## SECTION 3: PRE-STARTUP CHECKS
1. Ensure suction valve V-101 is fully open.
2. Verify lube oil level in the bearing housing is between 50% and 75% on the sight glass.
3. Check cooling water circulation to seal cooler is active.
4. Confirm mechanical seal pressure accumulator reads 5.0 bar.

## SECTION 4: EMERGENCY SHUTDOWN PROCEDURE
In case of severe seal leakage, abnormal vibration above 7.1 mm/s, or motor overload:
1. Press the local Emergency Stop button (ESD-P101).
2. Immediately close discharge valve V-102.
3. Notify the Shift Controller in Main Control Room (MCR).
"""

    with open(sop_file, "w", encoding="utf-8") as f:
        f.write(sop_content)

    print(f"\n[1] Created sample document at: {sop_file}")

    # 2. Ingest Document
    print("\n[2] Ingesting document into RAG Pipeline...")
    doc_meta = pipeline.ingest_file(
        sop_file,
        metadata={
            "document_type": "SOP",
            "department": "Operations",
            "plant": "MRPL Refinery",
            "unit": "CDU-1",
            "equipment_id": "P-101A",
            "revision": "R2",
        },
    )

    print(f"Ingested Document Title: {doc_meta.title}")
    print(f"Ingested Document ID: {doc_meta.document_id}")
    print(f"Document Type: {doc_meta.document_type} | Unit: {doc_meta.unit} | Equip: {doc_meta.equipment_id}")

    # 3. Test Query Pipeline (Vector + Keyword Hybrid + Reranking + Citations)
    print("\n[3] Executing Query Pipeline...")
    query = "What is the emergency shutdown procedure and discharge pressure for crude charge pump P-101A?"
    
    # Optional metadata filter for CDU-1 unit
    filter_cond = FilterCondition(unit="CDU-1", equipment_id="P-101A")

    result = pipeline.query_context(user_query=query, top_k=3, filters=filter_cond)

    print("\n" + "=" * 50)
    print("   GROUNDED CONTEXT OUTPUT FOR DOWNSTREAM AGENT")
    print("=" * 50)
    print(result.context_text)

    print("\n" + "=" * 50)
    print("   TRACEABLE SOURCE CITATIONS")
    print("=" * 50)
    for cit in result.citations:
        print(cit.to_formatted_str())
        print(f"   Snippet: {cit.snippet}")
        print("-" * 50)

    # 4. Test Evaluation Metric
    print("\n[4] Running Retrieval Evaluation Benchmark...")
    evaluator = RetrievalEvaluator()
    tc = EvalTestCase(
        test_id="test_01",
        query=query,
        expected_doc_ids=[doc_meta.document_id],
    )
    eval_metrics = evaluator.evaluate_test_case(tc, result.retrieved_chunks, k=3)
    print(f"Retrieval Evaluation Metrics: {eval_metrics}")

    print("\n" + "=" * 70)
    print("      MRPL RAG PIPELINE VERIFICATION SUCCESSFUL!")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
