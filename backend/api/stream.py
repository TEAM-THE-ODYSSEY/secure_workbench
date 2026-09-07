from __future__ import annotations
import asyncio
from typing import Optional
from fastapi import APIRouter, Query, WebSocket, status
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketDisconnect, WebSocketState

try:
    from backend import engine_bridge, task_store
    from backend.auth_deps import get_current_user_ws
except ImportError:
    import engine_bridge, task_store
    from auth_deps import get_current_user_ws

router = APIRouter(tags=["stream"])


@router.websocket("/tasks/{task_id}/stream")
async def task_stream_ws(
    websocket: WebSocket,
    task_id: str,
    token: Optional[str] = Query(None),
):
    """WebSocket stream for task execution events.

    Iterates engine_bridge.subscribe(task_id) and streams status_change,
    tool_call, agent_handoff, and final events to the connected client.
    """
    # 1. Accept websocket connection
    await websocket.accept()

    # 2. Validate authentication token (via ?token= query param or header)
    user = await get_current_user_ws(websocket, token)
    if user is None:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Unauthorized",
        )
        return

    # 3. On connect, if task_id doesn't exist, close with an appropriate code
    if not task_store.exists(task_id):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Task not found",
        )
        return

    # 4. Stream events from engine_bridge.subscribe(task_id)
    try:
        async for event in engine_bridge.subscribe(task_id):
            payload = jsonable_encoder(event)
            await websocket.send_json(payload)
            # After the final event is sent, stop streaming
            if event.get("event") == "final":
                break
    except (WebSocketDisconnect, asyncio.CancelledError):
        # Client closed connection early — cancel subscription loop cleanly
        return
    except Exception:
        # Handle unexpected socket errors gracefully without crashing the server task
        return
    finally:
        # Close connection cleanly if still connected
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
        except Exception:
            pass
