"""Auth router: register, login, logout, refresh, me.

Rate limiting: custom in-memory, 5 attempts/minute/IP for auth endpoints.
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api import auth as auth_utils
from api.dependencies import get_current_user, get_db
from api.schemas import AuthResponse
from api.services import auth_service
from db.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory rate limiter: {prefix: {ip: [timestamp, ...]}}
_attempts: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 5


def _check_rate_limit(ip: str, prefix: str = "auth") -> None:
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW
    bucket = _attempts[prefix][ip]
    _attempts[prefix][ip] = [t for t in bucket if t > window_start]
    if len(_attempts[prefix][ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak percobaan. Coba lagi dalam 1 menit.",
        )
    _attempts[prefix][ip].append(now)


class AuthBody(BaseModel):
    email: str
    password: str


def _set_cookies(response: Response, ar: AuthResponse) -> None:
    if ar.access_token:
        response.set_cookie(
            key="access_token",
            value=ar.access_token,
            httponly=True,
            secure=False,  # local dev; set True in production
            samesite="lax",
            max_age=60 * auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES,
            path="/",
        )
    if ar.refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=ar.refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=60 * 60 * 24 * auth_utils.REFRESH_TOKEN_EXPIRE_DAYS,
            path="/",
        )


def _clear_cookies(response: Response) -> None:
    for key in ("access_token", "refresh_token"):
        response.delete_cookie(key, path="/")


@router.post("/register", response_model=AuthResponse)
def register(
    body: AuthBody,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    _check_rate_limit(request.client.host if request.client else "unknown", "auth")
    ar = auth_service.register(db, body.email.strip(), body.password)
    if ar.status == "ok":
        _set_cookies(response, ar)
    return ar


@router.post("/login", response_model=AuthResponse)
def login(
    body: AuthBody,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    _check_rate_limit(request.client.host if request.client else "unknown", "auth")
    ar = auth_service.login(db, body.email.strip(), body.password)
    if ar.status == "ok":
        _set_cookies(response, ar)
    return ar


@router.post("/logout", response_model=AuthResponse)
def logout(response: Response) -> AuthResponse:
    _clear_cookies(response)
    return AuthResponse(status="ok", message="Logged out.")


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    _check_rate_limit(request.client.host if request.client else "unknown", "auth")
    token = request.cookies.get("refresh_token", "")
    if not token:
        return AuthResponse(status="error", message="Tidak ada token refresh.")
    ar = auth_service.refresh(db, token)
    if ar.status == "ok":
        _set_cookies(response, ar)
    return ar


@router.get("/me", response_model=AuthResponse)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthResponse:
    return auth_service.get_me(db, current_user)
