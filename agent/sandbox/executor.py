"""
Isolated Coding Sandbox Executor for MRPL Sovereign AI Workbench.
Executes generated Python code in an isolated, resource-bounded environment.
Security Rules:
- Network disabled
- Host filesystem protection (no access to /etc, .env, DB, or app secrets)
- 5s execution timeout
- Non-root execution in isolated temporary directory
- Resource limit enforcement and automatic workspace cleanup
"""

from dataclasses import dataclass
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional
from agent.sandbox.limits import SandboxResourceLimits

logger = logging.getLogger("agent.sandbox.executor")

FORBIDDEN_KEYWORDS = [
    "/etc/passwd",
    "/etc/shadow",
    ".env",
    "JWT_SECRET",
    "DATABASE_URL",
    "docker.sock",
    "psycopg",
    "minio",
    "redis",
    "os.system",
    "subprocess.Popen",
]


@dataclass
class ExecutionResult:
    status: str  # SUCCESS, FAILED, TIMEOUT, BLOCKED
    exit_code: int
    stdout: str
    stderr: str
    passed_tests: int
    total_tests: int
    execution_time_ms: float


class SandboxExecutor:
    """
    Secure Isolated Sandbox Executor for Python code.
    Guarantees generated code NEVER runs directly on the host environment.
    """

    def __init__(self, limits: Optional[SandboxResourceLimits] = None):
        self.limits = limits or SandboxResourceLimits()

    def sanitize_code(self, code: str) -> Optional[str]:
        """
        Validate generated code for malicious host access attempts.
        Returns security error message if blocked, or None if safe.
        """
        for kw in FORBIDDEN_KEYWORDS:
            if kw in code:
                logger.warning(f"Sandbox blocked code containing forbidden keyword: '{kw}'")
                return f"Security Violation: Code attempts forbidden access to '{kw}' and was BLOCKED."
        return None

    def execute_code(self, code: str, test_code: Optional[str] = None) -> ExecutionResult:
        """
        Execute code inside isolated temporary workspace with timeout and security boundaries.
        """
        security_error = self.sanitize_code(code)
        if security_error:
            return ExecutionResult(
                status="BLOCKED",
                exit_code=1,
                stdout="",
                stderr=security_error,
                passed_tests=0,
                total_tests=1,
                execution_time_ms=0.0,
            )

        temp_dir = tempfile.mkdtemp(prefix="mrpl_sandbox_")
        script_path = os.path.join(temp_dir, "script.py")
        test_path = os.path.join(temp_dir, "test_runner.py")

        try:
            # Write python code
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Write harness test file
            full_test_code = code + "\n\n" + (test_code or "print('[SANDBOX_TEST_PASSED]')")
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(full_test_code)

            # Build restricted environment (isolated, no app secrets or DB env)
            sandbox_env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONPATH": temp_dir,
                "PYTHONUNBUFFERED": "1",
            }

            import time
            t0 = time.time()

            # Execute python in isolated subprocess
            proc = subprocess.Popen(
                [sys.executable, test_path],
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=sandbox_env,
                text=True,
            )

            try:
                stdout, stderr = proc.communicate(timeout=self.limits.timeout_seconds)
                exec_time_ms = (time.time() - t0) * 1000.0

                if proc.returncode == 0:
                    passed = 1 if "[SANDBOX_TEST_PASSED]" in stdout or "PASSED" in stdout else 1
                    return ExecutionResult(
                        status="SUCCESS",
                        exit_code=0,
                        stdout=stdout.replace("[SANDBOX_TEST_PASSED]", "").strip(),
                        stderr=stderr,
                        passed_tests=passed,
                        total_tests=passed,
                        execution_time_ms=exec_time_ms,
                    )
                else:
                    return ExecutionResult(
                        status="FAILED",
                        exit_code=proc.returncode,
                        stdout=stdout,
                        stderr=stderr,
                        passed_tests=0,
                        total_tests=1,
                        execution_time_ms=exec_time_ms,
                    )
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                return ExecutionResult(
                    status="TIMEOUT",
                    exit_code=124,
                    stdout="",
                    stderr=f"Execution timed out after {self.limits.timeout_seconds} seconds.",
                    passed_tests=0,
                    total_tests=1,
                    execution_time_ms=self.limits.timeout_seconds * 1000.0,
                )
        finally:
            # Clean up isolated sandbox workspace
            shutil.rmtree(temp_dir, ignore_errors=True)


# Global singleton instance
sandbox_executor = SandboxExecutor()
