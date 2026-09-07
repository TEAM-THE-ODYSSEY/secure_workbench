"""
Compatibility wrapper for agent.models.model_manager.
Re-exports unified ModelManager from agent.model_manager.
"""

from agent.model_manager import (
    ModelManager,
    ModelManagerError,
    InfrastructureError,
    QualityFailureError,
)

__all__ = [
    "ModelManager",
    "ModelManagerError",
    "InfrastructureError",
    "QualityFailureError",
]
