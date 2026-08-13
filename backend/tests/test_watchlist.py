"""Watchlist tests: auth protection, CRUD, authorization isolation."""
from __future__ import annotations

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

EMAIL_A = "watchlist_a@obliq.test"
EMAIL_B = "watchlist_b@obliq.test"
PASSWORD = "rahasia123"


def _register(client, email: str) -> str:
    resp = client.post("/api/auth/register", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200
    return resp.json()["access_token"]


class TestWatchlistAPI:
    @pytest.fixture(autouse=True)
    def _cleanup(self) -> None:
        from api.dependencies import get_db
        from api.routers.auth import _attempts
        from db.models import User, WatchlistItem
        _attempts.clear()
        gen = get_db()
        db = next(gen)
        try:
            for email in (EMAIL_A, EMAIL_B):
                user = db.scalars(
                    __import__("sqlalchemy").select(User).where(User.email == email)
                ).first()
                if user:
                    db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).delete()
                    db.delete(user)
            db.commit()
        finally:
            db.close()

    def _client(self) -> TestClient:
        from api.main import app
        return TestClient(app)

    def _auth_headers(self, token: str) -> dict:
        return {"Cookie": f"access_token={token}"}

    def test_list_without_auth_returns_401(self) -> None:
        resp = self._client().get("/api/watchlist")
        assert resp.status_code == 401

    def test_add_without_auth_returns_401(self) -> None:
        resp = self._client().post("/api/watchlist", json={"item_type": "stock", "item_code": "BBCA"})
        assert resp.status_code == 401

    def test_delete_without_auth_returns_401(self) -> None:
        resp = self._client().delete("/api/watchlist/1")
        assert resp.status_code == 401

    def test_add_and_list(self) -> None:
        client = self._client()
        token = _register(client, EMAIL_A)
        headers = self._auth_headers(token)

        resp = client.post("/api/watchlist", json={"item_type": "stock", "item_code": "BBCA"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        resp = client.get("/api/watchlist", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["count"] == 1
        assert data["items"][0]["item_code"] == "BBCA"
        assert data["items"][0]["item_type"] == "stock"

    def test_add_duplicate_returns_empty(self) -> None:
        client = self._client()
        token = _register(client, EMAIL_A)
        headers = self._auth_headers(token)
        client.post("/api/watchlist", json={"item_type": "stock", "item_code": "BBCA"}, headers=headers)
        resp = client.post("/api/watchlist", json={"item_type": "stock", "item_code": "BBCA"}, headers=headers)
        assert resp.json()["status"] == "empty"
        assert "sudah ada" in resp.json()["message"]

    def test_invalid_type(self) -> None:
        client = self._client()
        token = _register(client, EMAIL_A)
        resp = client.post("/api/watchlist", json={"item_type": "invalid", "item_code": "X"}, headers=self._auth_headers(token))
        assert resp.json()["status"] == "empty"

    def test_delete_own_item(self) -> None:
        client = self._client()
        token = _register(client, EMAIL_A)
        headers = self._auth_headers(token)
        add = client.post("/api/watchlist", json={"item_type": "stock", "item_code": "BBCA"}, headers=headers)
        item_id = add.json()["items"][0]["id"]

        resp = client.delete(f"/api/watchlist/{item_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        resp = client.get("/api/watchlist", headers=headers)
        assert resp.json()["count"] == 0

    def test_cannot_delete_other_users_item(self) -> None:
        client = self._client()
        token_a = _register(client, EMAIL_A)
        token_b = _register(client, EMAIL_B)
        add = client.post("/api/watchlist", json={"item_type": "stock", "item_code": "BBCA"}, headers=self._auth_headers(token_a))
        item_id = add.json()["items"][0]["id"]

        resp = client.delete(f"/api/watchlist/{item_id}", headers=self._auth_headers(token_b))
        assert resp.status_code == 200
        assert resp.json()["status"] == "empty"
        assert "bukan milik" in resp.json()["message"]

    def test_cannot_list_other_users_items(self) -> None:
        client = self._client()
        token_a = _register(client, EMAIL_A)
        token_b = _register(client, EMAIL_B)
        client.post("/api/watchlist", json={"item_type": "stock", "item_code": "BBCA"}, headers=self._auth_headers(token_a))

        resp = client.get("/api/watchlist", headers=self._auth_headers(token_b))
        assert resp.json()["count"] == 0

    def test_delete_nonexistent(self) -> None:
        client = self._client()
        token = _register(client, EMAIL_A)
        resp = client.delete("/api/watchlist/99999", headers=self._auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "empty"
