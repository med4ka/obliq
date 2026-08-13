"""FastAPI dependencies: DB session + auth.

Router -> service -> db query pattern (ARCHITECTURE.md 3): routers never touch
the session directly; they depend on `get_db` and forward the session to the
service layer.
"""
from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from api import auth as auth_utils
from db.connection import get_engine
from db.models import User

# One sessionmaker bound to the cached engine; prepared lazily so importing the
# API package does not force a DB connection at module load.
_sessionmaker = sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yields a database session for the lifetime of one request."""
    session = _sessionmaker()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Require a valid access_token cookie. Returns the User or raises 401."""
    token = request.cookies.get("access_token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Belum login.")
    payload = auth_utils.decode_token(token, expected_type="access")
    if payload is None:
        raise HTTPException(status_code=401, detail="Token tidak valid atau kedaluwarsa.")
    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Pengguna tidak ditemukan.")
    return user
