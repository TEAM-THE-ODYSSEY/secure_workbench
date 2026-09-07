from __future__ import annotations
from fastapi import APIRouter

try:
    from backend.schemas.shared_schemas import HealthResponse
except ImportError:
    from schemas.shared_schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        local_only=True,
        external_calls_enabled=False,
    )
