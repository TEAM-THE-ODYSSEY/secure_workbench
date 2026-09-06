import logging
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from rag.storage.postgres import RiskLevel
from .risk_scorer import RiskAssessment
from .prompt_injection_detector import PromptInjectionResult

logger = logging.getLogger(__name__)

class TrustGateDecision(str, Enum):
    APPROVED = "APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"

class TrustGateResult(BaseModel):
    decision: TrustGateDecision
    reason: str
    risk_assessment: RiskAssessment

class TrustGate:
    def evaluate(self, risk_assessment: RiskAssessment, has_malware: bool, prompt_injection_result: Optional[PromptInjectionResult], has_contradictions: bool) -> TrustGateResult:
        
        if has_malware or risk_assessment.risk_score >= 0.9:
            return TrustGateResult(
                decision=TrustGateDecision.REJECTED,
                reason="Malware detected or critical risk score",
                risk_assessment=risk_assessment
            )
            
        if (prompt_injection_result and prompt_injection_result.is_suspicious and prompt_injection_result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]) or risk_assessment.risk_score >= 0.7:
            return TrustGateResult(
                decision=TrustGateDecision.QUARANTINED,
                reason="High risk prompt injection or high risk score",
                risk_assessment=risk_assessment
            )
            
        if has_contradictions or risk_assessment.risk_score >= 0.4:
            return TrustGateResult(
                decision=TrustGateDecision.REVIEW_REQUIRED,
                reason="Contradictions found or medium risk score",
                risk_assessment=risk_assessment
            )
            
        return TrustGateResult(
            decision=TrustGateDecision.APPROVED,
            reason="All security checks passed",
            risk_assessment=risk_assessment
        )
