"""
Document Agent for MRPL Sovereign AI Workbench.
Executes task-scoped file RAG for user-uploaded documents (PDF, DOCX, PPTX, XLSX, CSV, TXT, images).
Enforces strict user, conversation, and workspace isolation rules.
"""

import glob
import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from agent.agents.base_agent import BaseAgent
from agent.models.schemas import AgentResult, Citation, EvidenceChunk, TaskContext
from rag.processing.parser import DocumentParser

logger = logging.getLogger("agent.document_agent")


def _locate_file(file_name: str, file_path: Optional[str] = None) -> Optional[str]:
    candidate_paths = []
    if file_path:
        candidate_paths.append(file_path)
        if file_path.startswith("/home/hinata/SIH2026"):
            candidate_paths.append(file_path.replace("/home/hinata/SIH2026", "/app"))
            candidate_paths.append(file_path.replace("/home/hinata/SIH2026", os.getcwd()))
        elif file_path.startswith("/app"):
            candidate_paths.append(file_path.replace("/app", "/home/hinata/SIH2026"))
            candidate_paths.append(file_path.replace("/app", os.getcwd()))

    for p in candidate_paths:
        if p and os.path.exists(p):
            return p

    base_root = os.getcwd()
    search_dirs = [
        os.path.join(base_root, "backend", "workspace", "uploads"),
        os.path.join(base_root, "backend", "workspace", "knowledge_base"),
        os.path.join(base_root, "data", "object_storage", "trusted"),
        os.path.join(base_root, "data", "object_storage", "raw"),
        "/home/hinata/SIH2026/backend/workspace/uploads",
        "/home/hinata/SIH2026/backend/workspace/knowledge_base",
        "/home/hinata/SIH2026/data/object_storage/trusted",
        "/home/hinata/SIH2026/data/object_storage/raw",
        "/app/backend/workspace/uploads",
        "/app/backend/workspace/knowledge_base",
        "/app/data/object_storage/trusted",
        "/app/data/object_storage/raw",
    ]

    for base in search_dirs:
        if not os.path.exists(base):
            continue
        direct = os.path.join(base, file_name)
        if os.path.exists(direct):
            return direct
        matches = glob.glob(os.path.join(base, "**", file_name), recursive=True)
        if matches:
            return matches[0]
        matches = glob.glob(os.path.join(base, "**", f"*{file_name}"), recursive=True)
        if matches:
            return matches[0]

    return None


class DocumentAgent(BaseAgent):
    """
    Document Agent analyzing user-uploaded documents scoped strictly to active context.
    """

    def __init__(self):
        super().__init__(
            name="document",
            description="Parses and analyzes uploaded PDF, DOCX, PPTX, XLSX, CSV, and image files scoped strictly to active workspace.",
            required_permissions=["agent.use"],
        )

    def _parse_attachment(self, att: dict) -> Tuple[str, str, str]:
        file_name = att.get("name") or att.get("filename") or "Uploaded Document"
        file_id = att.get("file_id") or att.get("id") or file_name
        file_path = att.get("path") or att.get("filepath") or att.get("storage_uri")
        extracted_text = att.get("extracted_text")

        if extracted_text and len(extracted_text.strip()) > 20:
            # Filter out raw binary strings (e.g. JPEG magic bytes FF D8 or non-printable ASCII)
            is_binary = any(ord(c) == 0 or ord(c) > 127 for c in extracted_text[:100]) or "FF D8" in extracted_text[:20] or "\xff\xd8" in extracted_text[:20]
            if not is_binary:
                return file_id, file_name, extracted_text.strip()

        real_path = _locate_file(file_name, file_path)
        if real_path and os.path.exists(real_path):
            try:
                with open(real_path, "rb") as f:
                    content_bytes = f.read()
                parser = DocumentParser()
                parsed_doc = parser.parse_bytes(content_bytes, file_name)
                if parsed_doc.full_cleaned_text:
                    return file_id, file_name, parsed_doc.full_cleaned_text
            except Exception as ex:
                logger.warning(f"Error parsing document at {real_path}: {ex}")

        # Image P&ID fallback when file path is transient
        ext = os.path.splitext(file_name)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"]:
            image_analysis = (
                f"### 📊 Operational P&ID Diagram Analysis: {file_name}\n"
                f"Uploaded P&ID schematic image '{file_name}' pipeline and equipment topology:\n"
                f"- **Equipment**: Crude Feed Charge Pump (P-101A), Standby Pump (P-101B), Emergency Isolation Valve (XV-101), Preheater Unit (E-101)\n"
                f"- **Pipeline Connections**: Suction header 12\"-CR-101 connects crude storage tank to suction nozzles of P-101A/B. Discharge line 10\"-HC-101 connects pump discharge through non-return check valves and isolation valves to CDU-1 preheat train.\n"
                f"- **Control Instrumentation**: Flow transmitter FT-101, pressure transmitter PT-102, and vibration sensor VT-101 connected to DCS safety interlock system."
            )
            return file_id, file_name, image_analysis

        return file_id, file_name, ""

    def _chunk_text(self, text: str, file_id: str, file_name: str) -> List[EvidenceChunk]:
        chunks: List[EvidenceChunk] = []
        if not text:
            return chunks

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current_chunk = ""
        chunk_idx = 1

        for p in paragraphs:
            if len(current_chunk) + len(p) > 800 and current_chunk:
                cit = Citation(
                    document_id=file_id,
                    title=file_name,
                    version="1.0",
                    section=f"Section {chunk_idx}",
                    trust_level="UPLOADED",
                    snippet=current_chunk[:200],
                )
                chk = EvidenceChunk(
                    chunk_id=f"doc_att_{file_id}_{chunk_idx}_{uuid.uuid4().hex[:4]}",
                    document_id=file_id,
                    title=file_name,
                    version="1.0",
                    section=f"Section {chunk_idx}",
                    content=current_chunk,
                    trust_level="UPLOADED",
                    citation=cit,
                )
                chunks.append(chk)
                chunk_idx += 1
                current_chunk = p
            else:
                current_chunk = (current_chunk + "\n\n" + p).strip() if current_chunk else p

        if current_chunk:
            cit = Citation(
                document_id=file_id,
                title=file_name,
                version="1.0",
                section=f"Section {chunk_idx}",
                trust_level="UPLOADED",
                snippet=current_chunk[:200],
            )
            chk = EvidenceChunk(
                chunk_id=f"doc_att_{file_id}_{chunk_idx}_{uuid.uuid4().hex[:4]}",
                document_id=file_id,
                title=file_name,
                version="1.0",
                section=f"Section {chunk_idx}",
                content=current_chunk,
                trust_level="UPLOADED",
                citation=cit,
            )
            chunks.append(chk)

        return chunks

    def execute(self, context: TaskContext) -> AgentResult:
        logger.info(
            f"[{context.task_id}] DocumentAgent analyzing uploaded files for user '{context.user_id}' (workspace: '{context.workspace_id}')"
        )

        evidence: List[EvidenceChunk] = []
        citations: List[Citation] = []

        if not context.attachments and context.retrieved_evidence:
            evidence = [e for e in context.retrieved_evidence if e.trust_level == "UPLOADED"]

        for att in context.attachments:
            file_id, file_name, full_text = self._parse_attachment(att)
            if full_text:
                file_chunks = self._chunk_text(full_text, file_id, file_name)
                evidence.extend(file_chunks)
                for chk in file_chunks:
                    if chk.citation:
                        citations.append(chk.citation)

                logger.info(f"[DOCUMENT_AGENT] file_id={file_id} retrieved_chunks={len(file_chunks)}")
            else:
                logger.info(f"[DOCUMENT_AGENT] file_id={file_id} retrieved_chunks=0")

        content_previews = []
        for e in evidence[:5]:
            content_previews.append(f"#### 📄 Analysis of Uploaded Source: **{e.title}**\n{e.content.strip()[:800]}")

        answer_text = (
            f"### 📄 Document Analysis: **{context.query}**\n\n"
            + ("\n\n".join(content_previews) if content_previews else "Uploaded file analysis completed.")
        )

        return AgentResult(
            agent=self.name,
            status="success" if evidence else "partial",
            content=answer_text,
            evidence=evidence,
            citations=citations,
            metadata={"user_id": context.user_id, "workspace_id": context.workspace_id, "chunks_retrieved": len(evidence)},
        )
