"""Watchlist service: CRUD for user's saved bonds/stocks.

Every endpoint requires authentication (get_current_user dependency).
Users can only see/modify their own watchlist.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from api import schemas
from db.models import User, WatchlistItem


def list_items(session: Session, user: User) -> schemas.WatchlistResponse:
    items = session.scalars(
        select(WatchlistItem)
        .where(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.created_at.desc())
    ).all()
    if not items:
        return schemas.WatchlistResponse(status="empty", message="Watchlist kosong.")
    return schemas.WatchlistResponse(
        status="ok",
        count=len(items),
        items=[
            schemas.WatchlistItemSchema(
                id=i.id, item_type=i.item_type, item_code=i.item_code, created_at=i.created_at
            )
            for i in items
        ],
    )


def add_item(session: Session, user: User, item_type: str, item_code: str) -> schemas.WatchlistResponse:
    if item_type not in ("bond", "stock"):
        return schemas.WatchlistResponse(status="empty", message="Tipe item harus 'bond' atau 'stock'.")

    existing = session.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id,
            WatchlistItem.item_type == item_type,
            WatchlistItem.item_code == item_code,
        )
    )
    if existing is not None:
        return schemas.WatchlistResponse(status="empty", message="Item sudah ada di watchlist.")

    item = WatchlistItem(user_id=user.id, item_type=item_type, item_code=item_code.upper(), created_at=datetime.now())
    session.add(item)
    session.commit()
    session.refresh(item)
    return schemas.WatchlistResponse(
        status="ok",
        count=1,
        items=[
            schemas.WatchlistItemSchema(
                id=item.id, item_type=item.item_type, item_code=item.item_code, created_at=item.created_at
            )
        ],
    )


def delete_item(session: Session, user: User, item_id: int) -> schemas.WatchlistResponse:
    item = session.get(WatchlistItem, item_id)
    if item is None:
        return schemas.WatchlistResponse(status="empty", message="Item tidak ditemukan.")
    if item.user_id != user.id:
        return schemas.WatchlistResponse(status="empty", message="Item bukan milik Anda.")
    session.delete(item)
    session.commit()
    return schemas.WatchlistResponse(status="ok", message="Item dihapus.")
