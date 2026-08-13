"""JWT + bcrypt auth utilities (Fase 4).

Fail fast: JWT_SECRET MUST be set in .env (minimum 32 characters).
App PANICS at startup with a clear exception if missing -- no fallback,
no auto-generate. Rationale: (1) API and scheduler are separate processes;
auto-generate would create different secrets -> cross-process tokens invalid;
(2) SYSTEM.md sec 1 honesty principle -- don't run with half-baked config
that silently causes bugs.

Token design:
  - access_token: 15 minute expiry, httpOnly cookie, used for API auth.
  - refresh_token: 7 day expiry, httpOnly cookie, used to mint new access tokens.
  - POST /api/auth/refresh exchanges a valid refresh_token for a new pair.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

_JWT_SECRET: str | None = None


def _get_secret() -> str:
    global _JWT_SECRET
    if _JWT_SECRET is not None:
        return _JWT_SECRET
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET tidak di-set di environment. "
            "Buat 1x via `python -c \"import secrets; print(secrets.token_hex(32))\"` "
            "dan simpan di .env."
        )
    if len(secret) < 32:
        raise RuntimeError(
            f"JWT_SECRET terlalu pendek ({len(secret)} karakter). "
            "Minimal 32 karakter. Buat ulang via secrets.token_hex(32)."
        )
    _JWT_SECRET = secret
    return _JWT_SECRET


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def _make_token(payload: dict[str, Any], expires_delta: timedelta) -> str:
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(data, _get_secret(), algorithm=JWT_ALGORITHM)


def create_access_token(user_id: int, email: str) -> str:
    return _make_token(
        {"sub": str(user_id), "email": email, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int, email: str) -> str:
    return _make_token(
        {"sub": str(user_id), "email": email, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except jwt.PyJWTError:
        return None
