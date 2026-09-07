from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("agentic_engine.resources")


@dataclass
class ResourceSnapshot:
    cpu_percent: float = 0.0
    ram_available_mb: float = 4096.0
    ram_total_mb: float = 16384.0
    vram_available_mb: float = 0.0
    vram_total_mb: float = 0.0
    has_cuda: bool = False
    active_concurrency: int = 0


class ResourceMonitor:
    """Monitors system RAM and GPU VRAM to ensure resource-aware model execution."""

    def __init__(self):
        self._cuda_available: Optional[bool] = None

    def get_snapshot(self, active_concurrency: int = 0) -> ResourceSnapshot:
        ram_avail = 4096.0
        ram_total = 16384.0
        cpu_pct = 0.0

        try:
            import psutil
            vm = psutil.virtual_memory()
            ram_avail = vm.available / (1024 * 1024)
            ram_total = vm.total / (1024 * 1024)
            cpu_pct = psutil.cpu_percent(interval=None)
        except Exception:
            pass

        has_cuda = False
        vram_avail = 0.0
        vram_total = 0.0

        try:
            import torch
            if torch.cuda.is_available():
                has_cuda = True
                free_b, total_b = torch.cuda.mem_get_info()
                vram_avail = free_b / (1024 * 1024)
                vram_total = total_b / (1024 * 1024)
        except Exception:
            pass

        return ResourceSnapshot(
            cpu_percent=cpu_pct,
            ram_available_mb=ram_avail,
            ram_total_mb=ram_total,
            vram_available_mb=vram_avail,
            vram_total_mb=vram_total,
            has_cuda=has_cuda,
            active_concurrency=active_concurrency,
        )

    def can_accommodate(self, vram_required_mb: int, ram_required_mb: int = 2048) -> bool:
        snap = self.get_snapshot()
        if snap.has_cuda and vram_required_mb > 0:
            return snap.vram_available_mb >= vram_required_mb
        return snap.ram_available_mb >= ram_required_mb
