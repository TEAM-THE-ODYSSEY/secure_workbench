from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from .llm import OllamaClient
from .sandbox import DockerSandbox


@dataclass
class CodeRun:
    code: str
    execution: object
    attempts: int
    final_explanation: str


class CodingWorkflow:
    """Generate -> extract -> statically check -> sandbox -> repair."""

    def __init__(self, llm: OllamaClient, sandbox: DockerSandbox | None = None, max_attempts: int = 3):
        self.llm = llm
        self.sandbox = sandbox or DockerSandbox()
        self.max_attempts = max(1, min(max_attempts, 3))

    @staticmethod
    def _extract_code(text: str) -> str:
        text = (text or "").strip()
        matches = re.findall(r"```(?:python|py)?\s*(.*?)```", text, re.S | re.I)
        if matches:
            return matches[0].strip()
        # If the model ignored the code-block instruction, only accept the
        # whole response if Python can parse it.
        try:
            ast.parse(text)
            return text
        except SyntaxError:
            return ""

    @staticmethod
    def _static_check(code: str) -> tuple[bool, str]:
        if not code.strip():
            return False, "The model did not return runnable Python code."
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return False, f"Generated output is not valid Python: {exc}"

        banned = {"subprocess", "socket", "requests", "urllib", "shutil"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in banned:
                        return False, f"Disallowed import: {alias.name}"
            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in banned:
                    return False, f"Disallowed import: {node.module}"
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"eval", "exec", "compile", "__import__"}:
                    return False, f"Disallowed function: {node.func.id}"
        return True, "static check passed"

    def run(self, user_text: str, context: str, model: str) -> CodeRun:
        prompt = f"""
You are a coding specialist.
USER REQUEST:
{user_text}

CONTEXT:
{context or '[none]'}

Return ONLY one runnable Python code block. No prose outside the code block.
For a debugging request, fix the supplied program rather than writing a generic tutorial.
Do not use network, subprocess, shell commands, or unsafe OS operations.
""".strip()

        draft = self.llm.generate(model, prompt)
        code = self._extract_code(draft)
        last = None
        last_error = ""

        for attempt in range(1, self.max_attempts + 1):
            ok, static_error = self._static_check(code)
            if not ok:
                last_error = static_error
            else:
                last = self.sandbox.execute_python(code)
                if last.success:
                    verify_prompt = f"""
The following Python program was executed successfully in the sandbox.

USER REQUEST:
{user_text}

CODE:
{code}

PROGRAM OUTPUT:
{last.stdout}

Explain the result and whether the implementation satisfies the request.
Do not invent execution results.
""".strip()
                    explanation = self.llm.generate(model, verify_prompt)
                    return CodeRun(code, last, attempt, explanation)
                last_error = last.stderr or last.stdout or "Sandbox execution failed."

            repair_prompt = f"""
Repair the Python program for this user request.

USER REQUEST:
{user_text}

CURRENT CODE:
{code or '[no valid Python was returned]'}

ERROR:
{last_error}

Return ONLY one corrected runnable Python code block.
Do not return explanations.
Do not use network, subprocess, shell commands, or unsafe OS operations.
""".strip()
            repaired = self.llm.generate(model, repair_prompt)
            new_code = self._extract_code(repaired)
            if not new_code:
                code = ""
            else:
                code = new_code

        return CodeRun(
            code=code,
            execution=last,
            attempts=self.max_attempts,
            final_explanation=(
                f"The generated code did not pass sandbox execution after {self.max_attempts} attempts.\n\n"
                f"Last error:\n{last_error}"
            ),
        )
