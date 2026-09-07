from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional
from passlib.context import CryptContext

from sqlalchemy import or_

from rag.storage.postgres import db_manager, UserModel, UserRole

try:
    from backend.schemas.auth import User
except ImportError:
    from schemas.auth import User

# Password hashing context using pbkdf2_sha256/bcrypt
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class UserAlreadyExistsError(Exception):
    pass


def _user_from_model(model: UserModel) -> User:
    role_str = "admin" if model.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value, "admin"] else "user"
    return User(
        user_id=model.id,
        username=model.employee_id,
        role=role_str,
        created_at=model.created_at.isoformat() if model.created_at else datetime.now(timezone.utc).isoformat(),
    )


async def ensure_seed_users() -> None:
    """Ensure default admin and operator user accounts exist in PostgreSQL."""
    session = db_manager.get_session()
    try:
        # 1. Default admin user
        admin = session.query(UserModel).filter(UserModel.employee_id == "admin").first()
        if not admin:
            admin_user = UserModel(
                id="user_admin_001",
                employee_id="admin",
                name="System Administrator",
                email="admin@mrpl.co.in",
                department="IT & Sovereign Security",
                password_hash=pwd_context.hash("admin123"),
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            session.add(admin_user)

        # 2. Default operator user
        operator = session.query(UserModel).filter(UserModel.employee_id == "operator").first()
        if not operator:
            op_user = UserModel(
                id="user_operator_001",
                employee_id="operator",
                name="Operations Engineer",
                email="operator@mrpl.co.in",
                department="Refinery Operations (CDU-1)",
                password_hash=pwd_context.hash("operator123"),
                role=UserRole.OPERATIONS_ENGINEER.value,
                is_active=True,
            )
            session.add(op_user)

        session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()


async def has_admin_user() -> bool:
    """Return True if at least one user with admin role exists."""
    await ensure_seed_users()
    session = db_manager.get_session()
    try:
        count = session.query(UserModel).filter(UserModel.role.in_([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value, "admin"])).count()
        return count > 0
    finally:
        session.close()


async def count_admin_users() -> int:
    """Return count of users with admin role."""
    await ensure_seed_users()
    session = db_manager.get_session()
    try:
        return session.query(UserModel).filter(UserModel.role.in_([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value, "admin"])).count()
    finally:
        session.close()


async def create_user(
    username: str,
    password: str,
    role: Literal["admin", "user"] = "user",
) -> User:
    """Create a new user with hashed password and role in PostgreSQL."""
    await ensure_seed_users()
    session = db_manager.get_session()
    try:
        existing = session.query(UserModel).filter(
            or_(UserModel.employee_id == username, UserModel.email == username)
        ).first()
        if existing:
            raise UserAlreadyExistsError(f"Username '{username}' is already taken")

        user_id = f"user_{uuid.uuid4().hex[:12]}"
        password_hash = pwd_context.hash(password)
        db_role = UserRole.ADMIN.value if role == "admin" else UserRole.EMPLOYEE.value

        user_model = UserModel(
            id=user_id,
            employee_id=username,
            name=username.capitalize(),
            password_hash=password_hash,
            role=db_role,
            is_active=True,
        )
        session.add(user_model)
        session.commit()
        return _user_from_model(user_model)
    except Exception as e:
        session.rollback()
        if isinstance(e, UserAlreadyExistsError):
            raise e
        raise e
    finally:
        session.close()


async def get_user_by_username(username: str) -> Optional[User]:
    await ensure_seed_users()
    session = db_manager.get_session()
    try:
        user_model = session.query(UserModel).filter(
            or_(UserModel.employee_id == username, UserModel.email == username)
        ).first()
        return _user_from_model(user_model) if user_model else None
    finally:
        session.close()


async def get_user_by_id(user_id: str) -> Optional[User]:
    await ensure_seed_users()
    session = db_manager.get_session()
    try:
        user_model = session.query(UserModel).filter(UserModel.id == user_id).first()
        return _user_from_model(user_model) if user_model else None
    finally:
        session.close()


async def verify_password(username: str, password: str) -> Optional[User]:
    """Verify credentials against PostgreSQL user store."""
    await ensure_seed_users()
    session = db_manager.get_session()
    try:
        user_model = session.query(UserModel).filter(
            or_(UserModel.employee_id == username, UserModel.email == username)
        ).first()
        if not user_model or not user_model.is_active:
            return None
        if not pwd_context.verify(password, user_model.password_hash):
            return None

        user_model.last_login = datetime.now(timezone.utc)
        session.commit()
        return _user_from_model(user_model)
    except Exception:
        session.rollback()
        return None
    finally:
        session.close()
