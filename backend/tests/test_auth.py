"""Auth unit tests: register, login, refresh, rate limit, fail-fast."""
from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from api import auth as auth_module

# Load .env so JWT_SECRET is available for token tests
load_dotenv()


class TestAuthUtils:
    def test_jwt_secret_missing_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("JWT_SECRET", raising=False)
        auth_module._JWT_SECRET = None
        with pytest.raises(RuntimeError, match="tidak di-set"):
            auth_module._get_secret()
        auth_module._JWT_SECRET = None  # reset for next test

    def test_jwt_secret_too_short_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", "short")
        auth_module._JWT_SECRET = None
        with pytest.raises(RuntimeError, match="terlalu pendek"):
            auth_module._get_secret()
        auth_module._JWT_SECRET = None

    def test_hash_verify_roundtrip(self) -> None:
        pw = "test-password-123"
        h = auth_module.hash_password(pw)
        assert auth_module.verify_password(pw, h) is True
        assert auth_module.verify_password("wrong", h) is False

    def test_create_and_decode_access_token(self) -> None:
        token = auth_module.create_access_token(1, "test@example.com")
        payload = auth_module.decode_token(token, "access")
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_refresh_token_rejected_by_access_decode(self) -> None:
        refresh = auth_module.create_refresh_token(1, "test@example.com")
        assert auth_module.decode_token(refresh, "access") is None

    def test_expired_token_returns_none(self) -> None:
        # Manually create token with -1s expiry
        from datetime import timedelta, timezone, datetime
        import jwt
        payload = {"sub": "1", "type": "access", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}
        token = jwt.encode(payload, auth_module._get_secret(), algorithm="HS256")
        assert auth_module.decode_token(token, "access") is None


class TestAuthAPI:
    """Integration tests against the live API + DB."""

    BASE_EMAIL = "auth_test@obliq.test"

    @pytest.fixture(autouse=True)
    def _cleanup(self) -> None:
        from api.dependencies import get_db
        from api.routers.auth import _attempts
        from db.models import User

        _attempts.clear()
        gen = get_db()
        db = next(gen)
        try:
            existing = db.scalars(
                __import__("sqlalchemy").select(User).where(User.email == self.BASE_EMAIL)
            ).all()
            for u in existing:
                db.delete(u)
            db.commit()
        finally:
            db.close()

    def _client(self) -> TestClient:
        from api.main import app
        return TestClient(app)

    def test_register_success(self) -> None:
        resp = self._client().post("/api/auth/register", json={"email": self.BASE_EMAIL, "password": "rahasia123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["user"]["email"] == self.BASE_EMAIL
        assert data["access_token"] is not None
        assert data["refresh_token"] is not None

    def test_register_duplicate_email(self) -> None:
        self._client().post("/api/auth/register", json={"email": self.BASE_EMAIL, "password": "rahasia123"})
        resp = self._client().post("/api/auth/register", json={"email": self.BASE_EMAIL, "password": "lain123"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"
        assert "sudah terdaftar" in resp.json()["message"]

    def test_login_wrong_password(self) -> None:
        self._client().post("/api/auth/register", json={"email": self.BASE_EMAIL, "password": "rahasia123"})
        resp = self._client().post("/api/auth/login", json={"email": self.BASE_EMAIL, "password": "salah"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"
        assert "salah" in resp.json()["message"]

    def test_login_wrong_email(self) -> None:
        resp = self._client().post("/api/auth/login", json={"email": "nobody@obliq.test", "password": "x"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"
        # Same generic error as wrong password (no enumeration)
        assert "salah" in resp.json()["message"]

    def test_login_success(self) -> None:
        self._client().post("/api/auth/register", json={"email": self.BASE_EMAIL, "password": "rahasia123"})
        resp = self._client().post("/api/auth/login", json={"email": self.BASE_EMAIL, "password": "rahasia123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["access_token"] is not None

    def test_me_unauthenticated(self) -> None:
        resp = self._client().get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_authenticated(self) -> None:
        reg = self._client().post("/api/auth/register", json={"email": self.BASE_EMAIL, "password": "rahasia123"})
        token = reg.json()["access_token"]
        resp = self._client().get("/api/auth/me", cookies={"access_token": token})
        assert resp.status_code == 200
        assert resp.json()["user"]["email"] == self.BASE_EMAIL

    def test_refresh_flow(self) -> None:
        reg = self._client().post("/api/auth/register", json={"email": self.BASE_EMAIL, "password": "rahasia123"})
        refresh = reg.json()["refresh_token"]
        resp = self._client().post("/api/auth/refresh", cookies={"refresh_token": refresh})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["access_token"] is not None

    def test_logout_clears_cookies(self) -> None:
        self._client().post("/api/auth/register", json={"email": self.BASE_EMAIL, "password": "rahasia123"})
        resp = self._client().post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_rate_limit(self) -> None:
        for _ in range(5):
            self._client().post("/api/auth/login", json={"email": "x@y.com", "password": "x"})
        resp = self._client().post("/api/auth/login", json={"email": "x@y.com", "password": "x"})
        assert resp.status_code == 429

    def test_refresh_rate_limit(self) -> None:
        reg = self._client().post("/api/auth/register", json={"email": self.BASE_EMAIL, "password": "rahasia123"})
        assert reg.status_code == 200
        refresh = reg.json()["refresh_token"]
        assert refresh is not None
        # register = 1 attempt; 4 more refreshes = 5 total, then 6th = 429
        for _ in range(4):
            resp = self._client().post("/api/auth/refresh", cookies={"refresh_token": refresh})
            assert resp.status_code == 200
            # use the new token each round so it stays valid
            refresh = resp.json()["refresh_token"]
        resp = self._client().post("/api/auth/refresh", cookies={"refresh_token": refresh})
        assert resp.status_code == 429
