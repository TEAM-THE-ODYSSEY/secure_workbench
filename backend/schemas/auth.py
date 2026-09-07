from typing import Literal
from pydantic import BaseModel

class User(BaseModel):
    user_id: str
    username: str
    role: Literal["admin", "user"] = "user"
    created_at: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: User
