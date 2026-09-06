import logging
from typing import List
from pydantic import BaseModel
from rag.storage.postgres import RiskLevel

logger = logging.getLogger(__name__)

class RiskAssessment(BaseModel):
    risk_score: float
    risk_level: RiskLevel
    factors: List[str]

class RiskScorer:
    def __init__(self):
        self.weights = {
            "source_trust": 0.25,
            "malware": 0.25,
            "integrity": 0.15,
            "prompt_injection": 0.20,
            "contradiction": 0.10,
            "duplicate": 0.05
        }
        
    def score(self, source_trust_score: float, has_malware: bool, is_valid: bool, has_prompt_injection: bool, has_contradiction: bool, is_duplicate: bool) -> RiskAssessment:
        factors = []
        
        # Base scores for each category
        scores = {}
        
        scores["source_trust"] = source_trust_score
        if source_trust_score > 0.5:
            factors.append("Untrusted source")
            
        scores["malware"] = 1.0 if has_malware else 0.0
        if has_malware:
            factors.append("Malware detected")
            
        scores["integrity"] = 1.0 if not is_valid else 0.0
        if not is_valid:
            factors.append("Integrity check failed")
            
        scores["prompt_injection"] = 1.0 if has_prompt_injection else 0.0
        if has_prompt_injection:
            factors.append("Prompt injection detected")
            
        scores["contradiction"] = 1.0 if has_contradiction else 0.0
        if has_contradiction:
            factors.append("Contradictions found")
            
        scores["duplicate"] = 1.0 if is_duplicate else 0.0
        if is_duplicate:
            factors.append("Duplicate content")
            
        total_score = sum(scores[k] * self.weights[k] for k in self.weights)
        
        if total_score >= 0.9:
            level = RiskLevel.CRITICAL
        elif total_score >= 0.7:
            level = RiskLevel.HIGH
        elif total_score >= 0.4:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
            
        return RiskAssessment(risk_score=total_score, risk_level=level, factors=factors)
