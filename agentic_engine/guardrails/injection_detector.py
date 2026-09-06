import re

PATTERNS = [
    r"ignore\s+(all|any|the|previous|prior)\s+instructions",
    r"disregard\s+(all|any|the|previous|prior)",
    r"forget\s+(all|any|the|previous|prior)\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"show\s+(me\s+)?(the\s+)?system\s+message",
    r"developer\s+message",
    r"jailbreak",
    r"bypass\s+(your|the)\s+(rules|safety|guardrails)",
    r"disable\s+(your\s+)?(guardrails|safety)",
    r"execute\s+this\s+without\s+restriction",
]

def detect_prompt_injection(text: str):
    for pattern in PATTERNS:
        if re.search(pattern, text or "", re.IGNORECASE):
            return True, pattern
    return False, None
