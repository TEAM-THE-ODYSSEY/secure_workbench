"""
Resource Limits and Security Boundaries for Coding Sandbox.
"""

from dataclasses import dataclass


@dataclass
class SandboxResourceLimits:
    """Security boundaries and resource bounds for sandbox execution."""
    timeout_seconds: float = 5.0
    max_memory_bytes: int = 256 * 1024 * 1024  # 256 MB
    max_cpu_percent: float = 80.0
    max_processes: int = 20
    network_enabled: bool = False
    allow_host_filesystem: bool = False
    allow_secrets_access: bool = False
    max_attempts: int = 3
