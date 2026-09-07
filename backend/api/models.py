from __future__ import annotations
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, status

try:
    from backend.schemas.shared_schemas import ModelInfo, ModelsListResponse
    from backend.schemas.models import AddModelRequest
    from backend.auth_deps import get_current_admin
    from backend import model_registry_store
except ImportError:
    from schemas.shared_schemas import ModelInfo, ModelsListResponse
    from schemas.models import AddModelRequest
    from auth_deps import get_current_admin
    import model_registry_store

logger = logging.getLogger("workbench.models")

router = APIRouter(tags=["models"])

OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"


@router.get("/models", response_model=ModelsListResponse)
async def list_models():
    """Public — returns every model in the persisted registry."""
    models = model_registry_store.get_all_models()
    return ModelsListResponse(models=models)


@router.post("/models", response_model=ModelsListResponse, status_code=201)
async def add_model(
    body: AddModelRequest,
    _admin=Depends(get_current_admin),
):
    """Admin-only — register a new model backed by a locally-pulled Ollama tag."""

    # 1. Reject duplicate model_id
    if model_registry_store.model_exists(body.model_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A model with model_id '{body.model_id}' already exists.",
        )

    # 2. Verify the ollama_tag is actually pulled locally
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(OLLAMA_TAGS_URL)
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Cannot reach Ollama at http://localhost:11434 — "
                "is the Ollama server running?"
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to query Ollama tags: {exc}",
        )

    pulled_tags: set[str] = set()
    for entry in data.get("models", []):
        name = entry.get("name", "")
        pulled_tags.add(name)
        # Ollama sometimes returns "model:tag" and sometimes "model:tag"
        # with a trailing hash — normalise by also accepting the base form
        if ":" in name:
            pulled_tags.add(name.split(":")[0])

    if body.ollama_tag not in pulled_tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Model '{body.ollama_tag}' is not pulled in Ollama yet — "
                f"run `ollama pull {body.ollama_tag}` first."
            ),
        )

    # c. If both checks pass, build a ModelInfo from the AddModelRequest fields and call model_registry_store.save_model(...)
    new_model = ModelInfo(
        model_id=body.model_id,
        model_name=body.model_name,
        model_type=body.model_type,
        capabilities=body.capabilities,
        context_length=body.context_length,
        quantization=body.quantization,
        memory_requirement=body.memory_requirement,
        supported_tasks=body.supported_tasks,
        ollama_tag=body.ollama_tag,
        is_default_for_tasks=body.is_default_for_tasks,
    )
    model_registry_store.save_model(new_model)
    logger.info(f"Admin added model '{body.model_id}' (ollama_tag={body.ollama_tag})")

    # d. Return the full updated ModelsListResponse via get_all_models()
    return ModelsListResponse(models=model_registry_store.get_all_models())
