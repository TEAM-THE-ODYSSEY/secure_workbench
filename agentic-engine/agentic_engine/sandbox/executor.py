"""
SandboxExecutor
----------------
Runs untrusted/agent-generated Python code in an isolated subprocess.

Design goals:
* No network access assumptions — the engine as a whole never calls
  external APIs, and this executor does not open any sockets itself.
* Hard wall-clock timeout so a runaway generation loop can't hang the
  engine.
* Resource limits (CPU time, memory, no forking) on POSIX systems via
  the `resource` module, applied in the child process before exec.
* Each run gets its own temp directory that is deleted afterwards, so
  agents can't leave state behind or read each other's files.

This is a process-level sandbox, not a container/VM. For a hackathon /
self-hosted workbench this is a reasonable first line of defense; if
you later need to run genuinely untrusted third-party code, put this
behind a container (e.g. nsjail, firejail, or a throwaway Docker
container) — the interface below (`execute(code) -> SandboxResult`)
would not need to change.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import resource  # POSIX only
except ImportError:  # pragma: no cover - Windows fallback
    resource = None


@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    returncode: Optional[int]
    timed_out: bool = False


def _limit_resources(memory_mb: int, cpu_seconds: int):
    """Applied inside the child process via subprocess `preexec_fn`."""

    def _apply():
        if resource is None:
            return
        mem_bytes = memory_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            # Prevent forking a swarm of subprocesses
            resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
        except (ValueError, OSError):
            # Some environments (containers, macOS) restrict which
            # limits can be lowered — fail open rather than crash.
            pass

    return _apply


class SandboxExecutor:
    """Executes a single Python snippet per call, fully isolated."""

    def __init__(
        self,
        timeout_seconds: int = 10,
        memory_mb: int = 256,
        cpu_seconds: int = 8,
        python_executable: Optional[str] = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.memory_mb = memory_mb
        self.cpu_seconds = cpu_seconds
        self.python_executable = python_executable or sys.executable

    def execute(self, code: str) -> SandboxResult:
        code = textwrap.dedent(code)

        with tempfile.TemporaryDirectory(prefix="agentic_sandbox_") as tmpdir:
            script_path = Path(tmpdir) / "snippet.py"
            script_path.write_text(code, encoding="utf-8")

            preexec_fn = (
                _limit_resources(self.memory_mb, self.cpu_seconds)
                if resource is not None
                else None
            )

            try:
                proc = subprocess.run(
                    [self.python_executable, str(script_path)],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    preexec_fn=preexec_fn,
                    env={"PATH": "/usr/bin:/bin"},  # minimal env, no secrets leak
                )
            except subprocess.TimeoutExpired as exc:
                return SandboxResult(
                    success=False,
                    stdout=exc.stdout or "",
                    stderr=(exc.stderr or "") + "\n[sandbox] execution timed out",
                    returncode=None,
                    timed_out=True,
                )

            return SandboxResult(
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
            )
