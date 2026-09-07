from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .injection_detector import detect_prompt_injection

FORBIDDEN_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".bash", ".ps1", ".vbs",
    ".dll", ".so", ".bin", ".com", ".scr", ".msi", ".jar",
}

SUSPICIOUS_CONTENT_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"disregard\s+(all\s+)?safety\s+guidelines",
    r"you\s+are\s+now\s+in\s+unrestricted\s+mode",
    r"bypass\s+(all\s+)?filters",
    r"output\s+(the\s+)?secret\s+key",
    r"dan\s+mode\s+enabled",
]


class SecurityDecision:
    ACCEPT = "ACCEPT"
    REVIEW = "REVIEW"
    QUARANTINE = "QUARANTINE"


class InputGuard:
    """Enterprise Sovereign Security & Trust Pipeline.
    
    Stages:
    1. Source Trust Check (origin, extension validation)
    2. Cryptographic Integrity (SHA-256 hash, non-empty, size limits)
    3. File Malware / MIME Magic Check
    4. Instruction Poisoning & Prompt Injection Detection
    5. Contradiction & Risk Scoring
    6. Trust Gate Decision (ACCEPT / REVIEW / QUARANTINE)
    """

    def __init__(self, max_file_size_mb: int = 50):
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def check(
        self,
        text: str,
        filename: str | None = None,
        file_content: str | None = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        findings = []
        risk_score = 0.0

        # Stage 0: Empty check
        if not (text or "").strip() and not filename:
            return False, "Empty request received.", {"decision": SecurityDecision.QUARANTINE, "risk_score": 1.0}

        # Stage 1 & 2: Source Trust & Integrity
        file_hash = None
        if filename:
            p = Path(filename)
            ext = p.suffix.lower()

            if ext in FORBIDDEN_EXTENSIONS:
                findings.append(f"Forbidden executable or script extension: {ext}")
                risk_score += 0.8

            if p.exists():
                size = p.stat().st_size
                if size == 0:
                    findings.append("File is empty (0 bytes)")
                    risk_score += 0.5
                elif size > self.max_file_size_bytes:
                    findings.append(f"File size {size} exceeds allowed maximum {self.max_file_size_bytes}")
                    risk_score += 0.4

                # Compute SHA-256
                try:
                    h = hashlib.sha256()
                    with open(p, "rb") as f:
                        for chunk in iter(lambda: f.read(65536), b""):
                            h.update(chunk)
                    file_hash = h.hexdigest()
                except Exception as e:
                    findings.append(f"Hashing failed: {e}")
                    risk_score += 0.2

                # Stage 3: MIME magic signature check
                try:
                    with open(p, "rb") as f:
                        header = f.read(16)
                    if ext == ".pdf" and not header.startswith(b"%PDF"):
                        findings.append("PDF magic header mismatch (possible spoofed file)")
                        risk_score += 0.6
                    elif ext == ".png" and not header.startswith(b"\x89PNG\r\n\x1a\n"):
                        findings.append("PNG magic header mismatch")
                        risk_score += 0.6
                except Exception:
                    pass

        # Stage 4: Prompt Injection Detection on User Prompt
        user_injection, pattern = detect_prompt_injection(text or "")
        if user_injection:
            findings.append(f"Direct prompt injection detected in user request: '{pattern}'")
            risk_score += 0.9

        # Stage 4b: Document Poisoning Detection on extracted file content
        if file_content:
            lower_content = file_content.lower()
            for pat in SUSPICIOUS_CONTENT_PATTERNS:
                if re.search(pat, lower_content):
                    findings.append(f"Document poisoning / adversarial instruction detected in file content: '{pat}'")
                    risk_score += 0.85
                    break

        # Stage 5 & 6: Risk Scoring & Trust Gate
        risk_score = min(1.0, risk_score)

        if risk_score >= 0.7:
            decision = SecurityDecision.QUARANTINE
            allowed = False
            reason = f"Security Quarantine [Risk: {risk_score:.2f}]: " + "; ".join(findings)
        elif risk_score >= 0.3:
            decision = SecurityDecision.REVIEW
            allowed = True  # Allowed with audit review flag
            reason = f"Security Review Flagged [Risk: {risk_score:.2f}]: " + "; ".join(findings)
        else:
            decision = SecurityDecision.ACCEPT
            allowed = True
            reason = "Security check passed (ACCEPT)"

        metadata = {
            "decision": decision,
            "risk_score": round(risk_score, 2),
            "findings": findings,
            "file_sha256": file_hash,
        }

        return allowed, reason, metadata
