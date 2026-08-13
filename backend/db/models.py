"""SQLAlchemy ORM models (Fase 1, formal).

Single source of truth for the DB schema consumed by the pipeline (storage layer)
and by Alembic migrations (target_metadata). Values that represent money/rates
must be Numeric/Decimal, never Float (SYSTEM.md 1.5).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MacroIndicator(Base):
    """One observation of a macro indicator (e.g. inflation_yoy) on one date.

    `source` + `fetched_at` are audit fields, part of the product (SCHEMA.md):
    every rendered number must be traceable to where it came from and when.
    """

    __tablename__ = "macro_indicators"
    __table_args__ = (
        # Idempotency key: re-fetching the same indicator/date must update,
        # never insert a duplicate row (ARCHITECTURE.md 4).
        UniqueConstraint(
            "indicator_type", "observation_date", name="uq_macro_type_date"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_type: Mapped[str] = mapped_column(
        String(50),
        comment="Enforced by CHECK constraint ck_macro_indicator_type at DB level",
    )
    observation_date: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    source: Mapped[str] = mapped_column(String(100))
    fetched_at: Mapped[datetime] = mapped_column(DateTime)


class Issuer(Base):
    """An issuer of debt instruments (corporate in Fase 2-3)."""

    __tablename__ = "issuers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(100))
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)


class Bond(Base):
    """Metadata for a single debt instrument (a SUN series e.g. FR0108).

    `code` is unique: the same series auctioned repeatedly must map to ONE row.
    `type` follows SCHEMA.md: government / corporate / sukuk_government /
    sukuk_corporate. Government SUN carry no issuer (issuer_id stays NULL).
    """

    __tablename__ = "bonds"
    __table_args__ = (
        UniqueConstraint("code", name="uq_bonds_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(30))
    issuer_id: Mapped[int | None] = mapped_column(
        ForeignKey("issuers.id"), nullable=True
    )
    coupon_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True
    )  # None = zero-coupon (SPN)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tenor_years: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class YieldObservation(Base):
    """One yield observation for one bond on one date (SCHEMA.md).

    Unique (bond_id, observation_date) is the idempotency key: re-fetching the
    same bond/date must update in place, never duplicate.
    """

    __tablename__ = "yield_observations"
    __table_args__ = (
        UniqueConstraint(
            "bond_id", "observation_date", name="uq_yield_bond_date"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bond_id: Mapped[int] = mapped_column(ForeignKey("bonds.id"))
    observation_date: Mapped[date] = mapped_column(Date)
    yield_value: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    source: Mapped[str] = mapped_column(String(100))
    fetched_at: Mapped[datetime] = mapped_column(DateTime)
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False)


class User(Base):
    """Registered user (Fase 4: auth + watchlist)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "item_code", name="uq_watchlist_user_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    item_type: Mapped[str] = mapped_column(String(10))  # "bond" | "stock"
    item_code: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
class Stock(Base):
    """Metadata for one stock/index (SCHEMA.md draft Fase S1)."""

    __tablename__ = "stocks"
    __table_args__ = (
        UniqueConstraint("code", name="uq_stocks_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30))
    symbol_yahoo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10))  # "index" / "equity"
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    board: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StockObservation(Base):
    """One daily OHLC/volume/adj_close observation (SCHEMA.md Fase S1)."""

    __tablename__ = "stock_observations"
    __table_args__ = (
        UniqueConstraint(
            "stock_id", "observation_date", name="uq_stock_obs_date"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"))
    observation_date: Mapped[date] = mapped_column(Date)
    open: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    high: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    close: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    adj_close: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(String(100))
    fetched_at: Mapped[datetime] = mapped_column(DateTime)
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False)