from .text_validator import TextValidator
from .json_validator import JsonValidator
from .math_validator import MathValidator
from .code_validator import CodeValidator
from .document_validator import DocumentValidator
from .evidence_validator import EvidenceValidator

VALIDATORS = {
    "text": TextValidator(),
    "json": JsonValidator(),
    "math": MathValidator(),
    "code": CodeValidator(),
    "document": DocumentValidator(),
    "evidence": EvidenceValidator(),
}

def get_validator(kind: str):
    return VALIDATORS.get(kind, VALIDATORS["text"])

