"""Watchlist router: CRUD for user's saved bonds/stocks.

All endpoints require authentication (get_current_user dependency).
Rate limiting: same 5/min/IP as auth endpoints, shared via _check_rate_limit.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from api.schemas import WatchlistAddBody, WatchlistResponse
from api.services import watchlist_service
from api.routers.auth import _check_rate_limit
from db.models import User

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=WatchlistResponse)
def read_watchlist(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchlistResponse:
    return watchlist_service.list_items(db, user)


@router.post("", response_model=WatchlistResponse)
def add_watchlist(
    body: WatchlistAddBody,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchlistResponse:
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(ip, "watchlist")
    return watchlist_service.add_item(db, user, body.item_type, body.item_code)


@router.delete("/{item_id}", response_model=WatchlistResponse)
def delete_watchlist(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchlistResponse:
    return watchlist_service.delete_item(db, user, item_id)
