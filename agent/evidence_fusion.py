"""
Evidence Fusion Layer for MRPL Sovereign AI Workbench.
Combines, deduplicates, and ranks evidence outputs from multiple agents into a bounded ContextPack.
Enforces Evidence Safety Rule: All retrieved content is treated strictly as DATA, never executable instructions.
"""

import logging
import re
from typing import Dict, List, Set
from agent.models.schemas import AgentResult, Citation, ContextPack, EvidenceChunk, TaskContext

logger = logging.getLogger("agent.evidence_fusion")

# Prompt injection patterns to sanitize/neutralize in retrieved data
PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"disregard (all )?prior (system )?prompts",
    r"you are now (an? )?unrestricted",
    r"system prompt override",
    r"execute host command",
]


class EvidenceFusion:
    """
    Combines evidence from DocumentAgent, KnowledgeAgent, PIDAgent, and CodingAgent.
    Produces a bounded ContextPack for final reasoning.
    """

    def __init__(self, max_context_chunks: int = 4):
        self.max_context_chunks = max_context_chunks

    def sanitize_evidence_text(self, text: str) -> str:
        """
        Sanitize text content to neutralize prompt injection attempts in retrieved data.
        Ensures evidence is treated strictly as DATA.
        """
        clean_text = text
        has_injection = False
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, clean_text, flags=re.IGNORECASE):
                has_injection = True
            clean_text = re.sub(pattern, "[PROMPT_INJECTION_REDACTED]", clean_text, flags=re.IGNORECASE)
        return f"<!-- DATA_ONLY_EVIDENCE -->\n{clean_text}"

    def fuse(self, evidence_chunks: List[EvidenceChunk]) -> ContextPack:
        """Convenience method to fuse raw evidence chunks."""
        # Filter out QUARANTINED chunks
        safe_chunks = [c for c in evidence_chunks if (c.trust_level or "").upper() != "QUARANTINED"]
        dummy_ctx = TaskContext(
            task_id="fuse_task",
            user_id="system",
            conversation_id="conv_fuse",
            query="fuse_query",
            retrieved_evidence=safe_chunks,
        )
        return self.fuse_agent_results(dummy_ctx, [])

    def fuse_agent_results(self, context: TaskContext, agent_results: List[AgentResult]) -> ContextPack:
        """
        Deduplicate, rank, and merge evidence from all completed agent steps.
        """
        fused_chunks: List[EvidenceChunk] = []
        fused_citations: List[Citation] = []
        fused_entities: Set[str] = set(context.entity_context or [])
        sources: List[Dict[str, str]] = []
        seen_chunk_ids: Set[str] = set()

        # 1. Process evidence from context initial state
        for chk in context.retrieved_evidence:
            if chk.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chk.chunk_id)
                chk.content = self.sanitize_evidence_text(chk.content)
                fused_chunks.append(chk)
                if chk.citation:
                    fused_citations.append(chk.citation)

        # 2. Process evidence from each agent result
        for res in agent_results:
            if res.status not in ("success", "partial"):
                continue

            # Merge entities from metadata
            if "entities" in res.metadata and isinstance(res.metadata["entities"], list):
                fused_entities.update(res.metadata["entities"])

            for chk in res.evidence:
                if chk.chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chk.chunk_id)
                    chk.content = self.sanitize_evidence_text(chk.content)
                    fused_chunks.append(chk)
                    if chk.citation and chk.citation not in fused_citations:
                        fused_citations.append(chk.citation)

            for cit in res.citations:
                if cit not in fused_citations:
                    fused_citations.append(cit)

        # 3. Rank evidence chunks by trust level and score
        def get_trust_rank(chk: EvidenceChunk) -> int:
            t = (chk.trust_level or "").upper()
            if t == "VERIFIED":
                return 3
            if t == "TRUSTED":
                return 2
            if t == "UPLOADED":
                return 1
            return 0

        fused_chunks.sort(key=lambda c: (get_trust_rank(c), getattr(c, 'score', 0.5)), reverse=True)

        # 4. Limit to max bounded context pack size
        bounded_chunks = fused_chunks[: self.max_context_chunks]

        # 5. Format sources drawer summary metadata
        for cit in fused_citations[:10]:
            sources.append({
                "title": cit.title or "MRPL Source Document",
                "category": "Knowledge Base" if cit.trust_level != "UPLOADED" else "Uploaded File",
                "meta": f"Page {cit.page or 1} • v{cit.version or '1.0'}",
                "badge": "Verified" if cit.trust_level == "VERIFIED" else ("Uploaded" if cit.trust_level == "UPLOADED" else "Trusted"),
                "badgeType": "verified" if cit.trust_level == "VERIFIED" else ("uploaded" if cit.trust_level == "UPLOADED" else "trusted"),
            })

        logger.info(f"[EVIDENCE_FUSION] input_chunks={len(fused_chunks)} selected_chunks={len(bounded_chunks)} citations={len(fused_citations)}")

        return ContextPack(
            task_id=context.task_id,
            query=context.query,
            evidence_chunks=bounded_chunks,
            citations=fused_citations,
            entities=list(fused_entities),
            sources=sources,
        )


# Global singleton instance
evidence_fusion = EvidenceFusion()
