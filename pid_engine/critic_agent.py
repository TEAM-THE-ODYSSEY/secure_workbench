from __future__ import annotations

from typing import Any


class PIDCriticAgent:
    """
    Validates a proposed P&ID reasoning answer.

    The critic checks:

        1. Evidence support
        2. Confidence
        3. Missing evidence
        4. Unsupported claims
        5. Human-review requirement
    """

    def __init__(
        self,
        minimum_confidence: float = 0.70,
    ):

        self.minimum_confidence = (
            minimum_confidence
        )

    # =========================================================
    # EVIDENCE LOOKUP
    # =========================================================

    @staticmethod
    def _evidence_map(
        evidence: list[dict[str, Any]],
    ):

        result = {}

        for item in evidence:

            payload = item.get(
                "payload",
                {},
            )

            evidence_id = payload.get(
                "evidence_id"
            )

            if evidence_id:

                result[
                    evidence_id
                ] = item

        return result

    # =========================================================
    # CHECK EVIDENCE
    # =========================================================

    def _check_evidence(
        self,
        reasoning: dict[str, Any],
        evidence: list[dict[str, Any]],
    ):

        evidence_map = (
            self._evidence_map(
                evidence
            )
        )

        referenced_ids = reasoning.get(
            "evidence_ids",
            [],
        )

        if not referenced_ids:

            return False, (
                "Reasoning agent did not provide "
                "evidence IDs."
            )

        missing = []

        for evidence_id in referenced_ids:

            if evidence_id not in evidence_map:

                missing.append(
                    evidence_id
                )

        if missing:

            return False, (
                "Referenced evidence does not exist: "
                + ", ".join(missing)
            )

        return True, (
            "All referenced evidence exists."
        )

    # =========================================================
    # CHECK CONFIDENCE
    # =========================================================

    def _check_confidence(
        self,
        reasoning: dict[str, Any],
    ):

        confidence = float(
            reasoning.get(
                "confidence",
                0.0,
            )
        )

        if confidence < self.minimum_confidence:

            return False, (
                f"Reasoning confidence "
                f"{confidence:.3f} is below "
                f"required threshold "
                f"{self.minimum_confidence:.3f}."
            )

        return True, (
            f"Confidence {confidence:.3f} "
            f"meets the threshold."
        )

    # =========================================================
    # CHECK ANSWER
    # =========================================================

    def _check_answer(
        self,
        reasoning: dict[str, Any],
    ):

        answer = reasoning.get(
            "answer",
            "",
        )

        if not answer:

            return False, (
                "Reasoning agent produced "
                "an empty answer."
            )

        return True, (
            "Reasoning agent produced "
            "a non-empty answer."
        )

    # =========================================================
    # MAIN CRITIC
    # =========================================================

    def critique(
        self,
        reasoning: dict[str, Any],
        evidence: list[dict[str, Any]],
        graph: Any = None,
    ) -> dict[str, Any]:

        checks = []

        # -----------------------------------------------------
        # Answer
        # -----------------------------------------------------

        answer_ok, answer_message = (
            self._check_answer(
                reasoning
            )
        )

        checks.append(
            {
                "check": "answer",
                "passed": answer_ok,
                "message": answer_message,
            }
        )

        # -----------------------------------------------------
        # Evidence
        # -----------------------------------------------------

        evidence_ok, evidence_message = (
            self._check_evidence(
                reasoning,
                evidence,
            )
        )

        checks.append(
            {
                "check": "evidence",
                "passed": evidence_ok,
                "message": evidence_message,
            }
        )

        # -----------------------------------------------------
        # Confidence
        # -----------------------------------------------------

        confidence_ok, confidence_message = (
            self._check_confidence(
                reasoning
            )
        )

        checks.append(
            {
                "check": "confidence",
                "passed": confidence_ok,
                "message": confidence_message,
            }
        )

        # -----------------------------------------------------
        # Agent review flag
        # -----------------------------------------------------

        needs_review = bool(
            reasoning.get(
                "needs_review",
                False,
            )
        )

        if needs_review:

            checks.append(
                {
                    "check": "agent_review_flag",
                    "passed": False,
                    "message": (
                        "Reasoning agent itself "
                        "requested human review."
                    ),
                }
            )

        # -----------------------------------------------------
        # Final decision
        # -----------------------------------------------------

        all_passed = all(
            item["passed"]
            for item in checks
        )

        if all_passed:

            decision = "PASS"

        elif (
            not evidence_ok
            or
            not confidence_ok
            or
            needs_review
        ):

            decision = "HUMAN_REVIEW"

        else:

            decision = "REJECT"

        return {
            "decision": decision,
            "checks": checks,
            "reasoning": reasoning,
            "confidence": float(
                reasoning.get(
                    "confidence",
                    0.0,
                )
            ),
        }