from __future__ import annotations
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
import jwt
from fastapi import Depends, Header, HTTPException, Query, WebSocket, status

try:
    from backend import auth_store
    from backend.schemas.auth import User
except ImportError:
    import auth_store
    from schemas.auth import User

SECRET_FILE_PATH = Path(
    os.getenv(
        "JWT_SECRET_PATH",
        Path(__file__).resolve().parent / "workspace" / ".jwt_secret",
    )
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


def get_jwt_secret() -> str:
    """Read the persisted 256-bit JWT signing secret from disk, or generate

    and save it on first boot. Ensures tokens remain valid across restarts.
    """
    SECRET_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SECRET_FILE_PATH.exists():
        secret = SECRET_FILE_PATH.read_text(encoding="utf-8").strip()
        if secret:
            return secret

    # Generate a random 256-bit value (32 bytes hex encoded = 64 characters)
    secret = secrets.token_hex(32)
    SECRET_FILE_PATH.write_text(secret, encoding="utf-8")
    return secret


def create_access_token(user: User) -> str:
    secret = get_jwt_secret()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user.user_id,
        "username": user.username,
        "exp": expire,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    secret = get_jwt_secret()
    return jwt.decode(token, secret, algorithms=[ALGORITHM])


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token_query: Optional[str] = Query(None, alias="token"),
) -> User:
    """Dependency that extracts and validates the Bearer token from Authorization header

    (or ?token= query param). Returns the authenticated User or raises 401 Unauthorized.
    """
    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed Authorization header, expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = parts[1]
    elif token_query:
        token = token_query

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_store.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
) -> Optional[User]:
    """Validate WebSocket authentication via query parameter ?token=<token>

    or Authorization header. Returns User if valid, None otherwise.
    """
    token_str = token
    if not token_str:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token_str = auth_header[7:].strip()

    if not token_str:
        return None

    try:
        payload = decode_access_token(token_str)
        user_id = payload.get("sub")
        if not user_id:
            return None
        return await auth_store.get_user_by_id(user_id)
    except Exception:
        return None


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the authenticated user has role='admin'.

    Raises 403 Forbidden if not an admin.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user

