"""Auth service: register, login, refresh, get_current_user.

No silent failure on credentials -- always return the same generic error for
wrong email OR wrong password to prevent user enumeration.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from api import auth as auth_utils
from api import schemas
from db.models import User


def register(
    session: Session, email: str, password: str
) -> schemas.AuthResponse:
    if not email or "@" not in email:
        return schemas.AuthResponse(
            status="error", message="Email tidak valid."
        )
    if len(password) < 6:
        return schemas.AuthResponse(
            status="error", message="Password minimal 6 karakter."
        )

    existing = session.scalar(select(User).where(User.email == email))
    if existing is not None:
        return schemas.AuthResponse(
            status="error", message="Email sudah terdaftar."
        )

    user = User(
        email=email,
        password_hash=auth_utils.hash_password(password),
        created_at=datetime.now(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    access_token = auth_utils.create_access_token(user.id, user.email)
    refresh_token = auth_utils.create_refresh_token(user.id, user.email)
    return schemas.AuthResponse(
        status="ok",
        user=schemas.UserInfo(id=user.id, email=user.email),
        access_token=access_token,
        refresh_token=refresh_token,
    )


def login(session: Session, email: str, password: str) -> schemas.AuthResponse:
    user = session.scalar(select(User).where(User.email == email))
    if user is None or not auth_utils.verify_password(password, user.password_hash):
        return schemas.AuthResponse(
            status="error",
            message="Email atau password salah.",
        )

    access_token = auth_utils.create_access_token(user.id, user.email)
    refresh_token = auth_utils.create_refresh_token(user.id, user.email)
    return schemas.AuthResponse(
        status="ok",
        user=schemas.UserInfo(id=user.id, email=user.email),
        access_token=access_token,
        refresh_token=refresh_token,
    )


def refresh(session: Session, refresh_token: str) -> schemas.AuthResponse:
    payload = auth_utils.decode_token(refresh_token, expected_type="refresh")
    if payload is None:
        return schemas.AuthResponse(
            status="error", message="Token refresh tidak valid atau kedaluwarsa."
        )

    user_id = int(payload["sub"])
    user = session.get(User, user_id)
    if user is None:
        return schemas.AuthResponse(
            status="error", message="Pengguna tidak ditemukan."
        )

    access_token = auth_utils.create_access_token(user.id, user.email)
    new_refresh = auth_utils.create_refresh_token(user.id, user.email)
    return schemas.AuthResponse(
        status="ok",
        user=schemas.UserInfo(id=user.id, email=user.email),
        access_token=access_token,
        refresh_token=new_refresh,
    )


def get_me(session: Session, current_user: User) -> schemas.AuthResponse:
    return schemas.AuthResponse(
        status="ok",
        user=schemas.UserInfo(id=current_user.id, email=current_user.email),
    )
