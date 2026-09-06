from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int
    command: str


class DockerSandbox:
    """
    Executes generated Python code in an isolated Docker container.

    Security baseline:
    - no network
    - read-only container filesystem
    - temporary writable /tmp
    - non-root user
    - memory/CPU/PID limits
    - timeout
    """

    def __init__(
        self,
        image: str = "python:3.11-slim",
        timeout: int = 20,
        memory: str = "512m",
        cpus: str = "1.0",
        pids_limit: int = 64,
    ):
        self.image = image
        self.timeout = timeout
        self.memory = memory
        self.cpus = cpus
        self.pids_limit = pids_limit

    def execute_python(self, code: str) -> ExecutionResult:
        with tempfile.TemporaryDirectory(prefix="agent-sandbox-") as tmp:
            host_file = Path(tmp) / "main.py"
            host_file.write_text(code, encoding="utf-8")

            cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                "--memory", self.memory,
                "--cpus", self.cpus,
                "--pids-limit", str(self.pids_limit),
                "--user", "65532:65532",
                "-v", f"{host_file}:/workspace/main.py:ro",
                "-w", "/workspace",
                self.image,
                "python", "main.py",
            ]

            try:
                completed = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
            except FileNotFoundError as exc:
                return ExecutionResult(
                    False, "", "Docker executable was not found.", -1,
                    " ".join(cmd)
                )
            except subprocess.TimeoutExpired as exc:
                return ExecutionResult(
                    False,
                    (exc.stdout or ""),
                    "Sandbox execution timed out.",
                    -1,
                    " ".join(cmd)
                )

            return ExecutionResult(
                completed.returncode == 0,
                completed.stdout[-12000:],
                completed.stderr[-12000:],
                completed.returncode,
                " ".join(cmd),
            )
