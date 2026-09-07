from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status

try:
    from backend import auth_store
    from backend.auth_deps import create_access_token, get_current_admin, get_current_user
    from backend.auth_store import UserAlreadyExistsError
    from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, User
except ImportError:
    import auth_store
    from auth_deps import create_access_token, get_current_admin, get_current_user
    from auth_store import UserAlreadyExistsError
    from schemas.auth import LoginRequest, RegisterRequest, TokenResponse, User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    try:
        # role is always 'user' for public registration
        user = await auth_store.create_user(req.username, req.password, role="user")
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    token = create_access_token(user)
    return TokenResponse(access_token=token, token_type="bearer", user=user)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = await auth_store.verify_password(req.username, req.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user)
    return TokenResponse(access_token=token, token_type="bearer", user=user)


@router.get("/me", response_model=User)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/admin-check", response_model=User)
async def admin_check(admin: User = Depends(get_current_admin)):
    return admin
