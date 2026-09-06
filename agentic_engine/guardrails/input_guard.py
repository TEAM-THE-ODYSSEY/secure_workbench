from .injection_detector import detect_prompt_injection

class InputGuard:
    """Pre-LLM deterministic gate."""

    def check(self, text: str, filename: str | None = None):
        if not (text or "").strip() and not filename:
            return False, "Empty request."

        matched, pattern = detect_prompt_injection(text or "")
        if matched:
            return False, f"Prompt-injection pattern detected: {pattern}"

        return True, "allowed"
