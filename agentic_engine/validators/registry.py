from __future__ import annotations

from typing import Dict, List, Optional
from .base import BaseValidator
from .chain import ValidatorChain
from .code_validator import CodeValidator
from .document_validator import DocumentValidator
from .evidence_validator import EvidenceValidator
from .json_validator import JsonValidator
from .math_validator import MathValidator
from .syntax_validator import SyntaxValidator
from .text_validator import TextValidator
from .topology_validator import TopologyValidator

VALIDATORS: Dict[str, BaseValidator] = {
    "text": TextValidator(),
    "json": JsonValidator(),
    "math": MathValidator(),
    "code": CodeValidator(),
    "syntax": SyntaxValidator(),
    "document": DocumentValidator(),
    "evidence": EvidenceValidator(),
    "topology": TopologyValidator(),
    "output": TextValidator(),
}


def get_validator(kind: str) -> BaseValidator:
    return VALIDATORS.get(kind.lower(), VALIDATORS["text"])


def build_validator_chain(names: List[str]) -> ValidatorChain:
    """Instantiates a sequential chain of validators by name."""
    validators = [VALIDATORS.get(name.lower(), VALIDATORS["text"]) for name in names]
    if not validators:
        validators = [VALIDATORS["text"]]
    return ValidatorChain(validators)


def get_default_chain_for_task(task_type: str) -> ValidatorChain:
    task_chains = {
        "mathematical": ["math"],
        "coding": ["syntax", "code"],
        "document": ["document"],
        "multimodal": ["document"],
        "pid": ["evidence", "topology"],
        "reasoning": ["text"],
    }
    chain_names = task_chains.get(task_type.lower(), ["text"])
    return build_validator_chain(chain_names)
