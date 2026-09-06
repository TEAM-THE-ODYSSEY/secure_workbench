import logging
from typing import Optional
from pydantic import BaseModel
from rag.config import config
from rag.storage.postgres import SourceType, TrustLevel

from .source_trust import SourceTrustManager
from .malware_scanner import ClamAVScanner, StubMalwareScanner, MalwareScanResult
from .integrity_checker import IntegrityChecker, IntegrityCheckResult
from .duplicate_detector import DuplicateDetector, DuplicateCheckResult
from .prompt_injection_detector import RuleBasedPromptInjectionDetector, PromptInjectionResult
from .contradiction_detector import RuleBasedContradictionDetector, ContradictionResult
from .risk_scorer import RiskScorer
from .trust_gate import TrustGate, TrustGateResult

logger = logging.getLogger(__name__)

class SecurityPipelineResult(BaseModel):
    source_trust: TrustLevel
    malware: MalwareScanResult
    integrity: IntegrityCheckResult
    duplicate: DuplicateCheckResult
    prompt_injection: Optional[PromptInjectionResult] = None
    contradiction: Optional[ContradictionResult] = None
    trust_gate_result: TrustGateResult

class SecurityPipeline:
    def __init__(self):
        self.source_manager = SourceTrustManager()
        self.malware_scanner = ClamAVScanner() if config.CLAMAV_ENABLED else StubMalwareScanner()
        self.integrity_checker = IntegrityChecker()
        self.duplicate_detector = DuplicateDetector()
        self.prompt_detector = RuleBasedPromptInjectionDetector() if config.PROMPT_INJECTION_ENABLED else None
        self.contradiction_detector = RuleBasedContradictionDetector() if config.CONTRADICTION_DETECTION_ENABLED else None
        self.risk_scorer = RiskScorer()
        self.trust_gate = TrustGate()

    def run(self, file_bytes: bytes, filename: str, text_content: str, source_type: SourceType, document_id: str) -> SecurityPipelineResult:
        logger.info(f"Running security pipeline for {filename}")
        
        # 1. Source Trust
        trust_level = self.source_manager.evaluate_source(source_type)
        source_trust_score = 0.0 if trust_level in [TrustLevel.TRUSTED, TrustLevel.VERIFIED] else 1.0
        
        # 2. Malware Scan
        malware_res = self.malware_scanner.scan(file_bytes, filename)
        
        # 3. Integrity Check
        integrity_res = self.integrity_checker.check(file_bytes, filename)
        
        # 4. Duplicate Check
        duplicate_res = self.duplicate_detector.check_duplicate(integrity_res.file_hash)
        
        # 5. Prompt Injection
        pi_res = None
        if self.prompt_detector:
            pi_res = self.prompt_detector.detect(text_content)
            
        # 6. Contradiction Detection
        contra_res = None
        if self.contradiction_detector:
            contra_res = self.contradiction_detector.detect(text_content, document_id)
            
        # 7. Risk Scoring
        risk_assessment = self.risk_scorer.score(
            source_trust_score=source_trust_score,
            has_malware=not malware_res.is_clean,
            is_valid=integrity_res.is_valid,
            has_prompt_injection=pi_res.is_suspicious if pi_res else False,
            has_contradiction=contra_res.has_contradictions if contra_res else False,
            is_duplicate=duplicate_res.is_duplicate
        )
        
        # 8. Trust Gate
        gate_result = self.trust_gate.evaluate(
            risk_assessment=risk_assessment,
            has_malware=not malware_res.is_clean,
            prompt_injection_result=pi_res,
            has_contradictions=contra_res.has_contradictions if contra_res else False
        )
        
        logger.info(f"Security pipeline completed for {filename}. Result: {gate_result.decision}")

        return SecurityPipelineResult(
            source_trust=trust_level,
            malware=malware_res,
            integrity=integrity_res,
            duplicate=duplicate_res,
            prompt_injection=pi_res,
            contradiction=contra_res,
            trust_gate_result=gate_result
        )

    def process_file(
        self,
        file_bytes: bytes,
        filename: str,
        source_id: str = "admin_upload",
        source_type: Optional[SourceType] = None,
        operator_role: str = "ADMIN",
        text_content: Optional[str] = None,
    ):
        """Convenience wrapper around run() returning unified result object."""
        import uuid
        from rag.processing.parser import DocumentParser

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        st = source_type or SourceType.ADMIN_UPLOAD

        if text_content is None:
            try:
                parser = DocumentParser()
                parsed = parser.parse_bytes(file_bytes, filename=filename)
                text_content = parsed.content
            except Exception:
                text_content = file_bytes.decode("utf-8", errors="ignore")

        res = self.run(
            file_bytes=file_bytes,
            filename=filename,
            text_content=text_content,
            source_type=st,
            document_id=doc_id,
        )

        class ProcessResultWrapper:
            def __init__(self, doc_id, res):
                self.document_id = doc_id
                self.gate_decision = res.trust_gate_result.decision.value
                self.trust_level = res.source_trust.value
                self.risk_score = res.trust_gate_result.risk_assessment.risk_score
                self.risk_level = res.trust_gate_result.risk_assessment.risk_level.value
                self.is_quarantined = self.gate_decision in ("QUARANTINED", "REJECTED")
                self.findings = []

        return ProcessResultWrapper(doc_id, res)

