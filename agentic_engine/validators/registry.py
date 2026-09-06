from .text_validator import TextValidator
from .json_validator import JsonValidator
from .math_validator import MathValidator
from .code_validator import CodeValidator

VALIDATORS = {
    "text": TextValidator(),
    "json": JsonValidator(),
    "math": MathValidator(),
    "code": CodeValidator(),
}

def get_validator(kind: str):
    return VALIDATORS.get(kind, VALIDATORS["text"])
