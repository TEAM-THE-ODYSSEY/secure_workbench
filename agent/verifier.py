"""
Deterministic Content Verifier for the Reasoning Mini-Agent V1.
Verifies grounding, citation presence, evidence mapping, document version matching, and TRUSTED status.
"""

import logging
from typing import List, Optional, Set
from pydantic import BaseModel

from agent.models import Citation, EvidenceChunk, StructuredPDFContent

logger = logging.getLogger("agent.verifier")


class VerificationResult(BaseModel):
    """Result of content verification check."""
    is_valid: bool
    unsupported_claims: List[str]
    missing_citations_count: int
    invalid_versions_count: int
    untrusted_sources_count: int


class ContentVerifier:
    """
    Deterministic Content Verifier enforcing strict grounding against retrieved evidence.
    """

    def verify(
        self,
        content: StructuredPDFContent,
        retrieved_evidence: List[EvidenceChunk],
    ) -> VerificationResult:
        """
        Verify that all claims, steps, and operating limits are traceable to retrieved trusted evidence.
        """
        unsupported_claims: List[str] = []
        missing_citations = 0
        invalid_versions = 0
        untrusted_sources = 0

        # Build index of valid evidence document IDs and versions
        evidence_doc_ids: Set[str] = {e.document_id for e in retrieved_evidence}
        evidence_versions: Set[str] = {f"{e.document_id}:{e.version}" for e in retrieved_evidence}
        evidence_texts: List[str] = [e.content.lower() for e in retrieved_evidence]

        def check_citations(citations: List[Citation], context_label: str):
            nonlocal missing_citations, invalid_versions, untrusted_sources
            if not citations:
                missing_citations += 1
                unsupported_claims.append(f"{context_label}: Missing citation reference.")
                return

            for cit in citations:
                if cit.trust_level not in ("TRUSTED", "VERIFIED", "APPROVED"):
                    untrusted_sources += 1
                    unsupported_claims.append(
                        f"{context_label}: Citation document '{cit.document_id}' has non-TRUSTED status '{cit.trust_level}'."
                    )

                if cit.document_id not in evidence_doc_ids:
                    unsupported_claims.append(
                        f"{context_label}: Cited document_id '{cit.document_id}' was not in retrieved evidence."
                    )

                doc_ver_key = f"{cit.document_id}:{cit.version}"
                if doc_ver_key not in evidence_versions:
                    invalid_versions += 1
                    unsupported_claims.append(
                        f"{context_label}: Cited version '{cit.version}' for document '{cit.document_id}' does not match active retrieved evidence."
                    )

        # 1. Verify procedure steps
        for step in content.procedure_steps:
            context = f"Step {step.step_number} ('{step.instruction[:40]}...')"
            check_citations(step.citations, context)

        # 2. Verify operating limits
        for limit in content.operating_limits:
            context = f"Operating Limit '{limit.parameter}' ({limit.value})"
            check_citations(limit.citations, context)

            # Check if operating limit value parameter is grounded in evidence text
            val_text = limit.value.lower()
            import re
            nums = re.findall(r'\d+(?:\.\d+)?', val_text)
            has_valid_citation = any(c.document_id in evidence_doc_ids for c in limit.citations)
            if nums and not has_valid_citation and not any(any(n in ev_text for n in nums) for ev_text in evidence_texts):
                unsupported_claims.append(
                    f"Operating Limit value '{limit.value}' for '{limit.parameter}' is not supported by retrieved evidence text."
                )

        # 3. Verify references
        if content.references:
            for ref in content.references:
                if ref.document_id not in evidence_doc_ids:
                    unsupported_claims.append(
                        f"Reference document_id '{ref.document_id}' not found in retrieved evidence."
                    )

        is_valid = len(unsupported_claims) == 0

        logger.info(
            f"Content verification result: is_valid={is_valid}, unsupported_claims_count={len(unsupported_claims)}"
        )

        return VerificationResult(
            is_valid=is_valid,
            unsupported_claims=unsupported_claims,
            missing_citations_count=missing_citations,
            invalid_versions_count=invalid_versions,
            untrusted_sources_count=untrusted_sources,
        )
