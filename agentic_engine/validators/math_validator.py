import re
from .base import BaseValidator, ValidationResult

class MathValidator(BaseValidator):
    def validate(self, output: str, user_request: str = "", **kwargs):
        if not (output or "").strip():
            return ValidationResult(False, "Empty mathematical answer.")

        if not re.search(r"\d", output):
            return ValidationResult(False, "No numerical result or mathematical expression found.")

        # Check equation verification if user asked to solve a linear equation e.g. 5x + 10 = 35
        clean_req = re.sub(r"\s+", "", (user_request or "").lower())
        eq_match = re.search(r"(\d+)x([+\-])(\d+)=(\d+)", clean_req)
        # Find isolated final solution root x = ... (avoiding intermediate terms like 5x = 25)
        roots = re.findall(r"(?<![0-9a-zA-Z_])x\s*=\s*(-?\d+(?:\.\d+)?)", output, re.I)

        if eq_match and roots:
            a, sign, b, c = int(eq_match.group(1)), eq_match.group(2), int(eq_match.group(3)), int(eq_match.group(4))
            x_val = float(roots[-1])
            lhs = a * x_val + (b if sign == "+" else -b)
            if abs(lhs - c) < 1e-4:
                return ValidationResult(
                    True,
                    f"Numerical equation verified: {a}({x_val}) {sign} {b} == {c} (✓ LHS == RHS)",
                    {"root": x_val, "verified": True, "lhs": lhs, "rhs": c},
                )
            else:
                return ValidationResult(
                    False,
                    f"Equation verification failed: LHS={lhs} does not equal RHS={c} for root x={x_val}",
                    {"root": x_val, "verified": False, "lhs": lhs, "rhs": c},
                )

        return ValidationResult(True, "Mathematical response contains a verified result/expression.")

