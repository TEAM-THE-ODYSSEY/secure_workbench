"""
Input Gateway module for normalized file upload, MIME validation, metadata extraction,
and safe handoff to the ingestion/security pipeline.
"""

from agent.gateway.input_gateway import InputGateway, ProcessedFileInput

__all__ = ["InputGateway", "ProcessedFileInput"]
