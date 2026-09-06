"""
P&ID capability package for Main AI Agent.
Exposes structured P&ID representations, tag entity linking, and topology queries.
"""

from agent.pid.schemas import PIDDiagramKnowledge, PIDEntity, PIDConnection, PIDSourceProvenance
from agent.pid.entity_linker import PIDEntityLinker
from agent.pid.topology import PIDTopologyEngine

__all__ = [
    "PIDDiagramKnowledge",
    "PIDEntity",
    "PIDConnection",
    "PIDSourceProvenance",
    "PIDEntityLinker",
    "PIDTopologyEngine",
]
