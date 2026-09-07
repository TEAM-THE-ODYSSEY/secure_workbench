from __future__ import annotations
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query, WebSocket, status
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketDisconnect, WebSocketState

try:
    from backend.schemas.network import NetworkStatus
    from backend.schemas.auth import User
    from backend.auth_deps import get_current_user, get_current_user_ws
    from backend import network_monitor
except ImportError:
    from schemas.network import NetworkStatus
    from schemas.auth import User
    from auth_deps import get_current_user, get_current_user_ws
    import network_monitor

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/status", response_model=NetworkStatus)
async def get_network_status(
    _user: User = Depends(get_current_user),
):
    """Retrieve current network sovereignty snapshot (local vs external connections)."""
    return network_monitor.snapshot()


@router.websocket("/stream")
async def network_stream(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """WebSocket stream pushing network sovereignty updates every ~3 seconds."""
    await websocket.accept()

    if token:
        user = await get_current_user_ws(websocket, token)
        if user is None:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Unauthorized",
            )
            return

    try:
        while True:
            current_status = network_monitor.snapshot()
            payload = jsonable_encoder(current_status)
            await websocket.send_json(payload)
            await asyncio.sleep(3.0)
    except (WebSocketDisconnect, asyncio.CancelledError):
        return
    except Exception:
        return
    finally:
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
        except Exception:
            pass
