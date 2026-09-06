import logging
import re
from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel
from rag.storage.postgres import RiskLevel

logger = logging.getLogger(__name__)

class Finding(BaseModel):
    pattern_category: str
    matched_text: str
    confidence: float

class PromptInjectionResult(BaseModel):
    is_suspicious: bool
    risk_level: RiskLevel
    findings: List[Finding]

class BasePromptInjectionDetector(ABC):
    @abstractmethod
    def detect(self, text: str) -> PromptInjectionResult:
        pass

class RuleBasedPromptInjectionDetector(BasePromptInjectionDetector):
    def __init__(self):
        self.ai_addressing_words = [r"\bai\b", r"\bassistant\b", r"\bsystem\b", r"\bbot\b", r"\bmodel\b", r"\byou are\b", r"\byour instructions\b"]
        
        # operator/human-directed language which reduces confidence of malicious intent
        self.operator_words = [r"\boperator\b", r"\bengineer\b", r"\btechnician\b", r"\bhuman\b", r"\bmanual\b"]
        
        self.patterns = {
            "system_override": [
                r"ignore previous instructions",
                r"override safety",
                r"bypass all restrictions",
            ],
            "role_manipulation": [
                r"you are now",
            ],
            "instruction_injection": [
                r"system:",
                r"execute this command",
            ],
            "data_exfiltration": [
                r"print your prompt",
                r"output your instructions",
            ]
        }
        
    def detect(self, text: str) -> PromptInjectionResult:
        findings = []
        text_lower = text.lower()
        
        has_ai_addressing = any(re.search(pat, text_lower) for pat in self.ai_addressing_words)
        has_operator_addressing = any(re.search(pat, text_lower) for pat in self.operator_words)
        
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    # Require AI addressing or explicit lack of operator addressing for sensitive patterns
                    if has_ai_addressing or not has_operator_addressing:
                        # Exclude benign mentions
                        if has_operator_addressing and not has_ai_addressing:
                            continue
                        
                        findings.append(Finding(
                            pattern_category=category,
                            matched_text=match.group(0),
                            confidence=0.9 if has_ai_addressing else 0.7
                        ))
                        
        if not findings:
            return PromptInjectionResult(is_suspicious=False, risk_level=RiskLevel.LOW, findings=[])
            
        return PromptInjectionResult(
            is_suspicious=True,
            risk_level=RiskLevel.HIGH, # Default high for prompt injection
            findings=findings
        )
