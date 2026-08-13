"""create stocks, stock_observations

Revision ID: a1b2c3d4e5f7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-11

Fase S1: Yahoo Finance pipeline stores daily OHLC/volume/adj_close for
Indonesian equities/indices. Tables follow SCHEMA.md draft (Sesi 28).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "stocks"):
        op.create_table(
            "stocks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(length=30), nullable=False),
            sa.Column("symbol_yahoo", sa.String(length=30), nullable=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("kind", sa.String(length=10), nullable=False),
            sa.Column("sector", sa.String(length=100), nullable=True),
            sa.Column("board", sa.String(length=50), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.UniqueConstraint("code", name="uq_stocks_code"),
        )
    if not _table_exists(conn, "stock_observations"):
        op.create_table(
            "stock_observations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stocks.id"), nullable=False),
            sa.Column("observation_date", sa.Date(), nullable=False),
            sa.Column("open", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("high", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("low", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("close", sa.Numeric(precision=14, scale=2), nullable=False),
            sa.Column("adj_close", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("volume", sa.BigInteger(), nullable=True),
            sa.Column("source", sa.String(length=100), nullable=False),
            sa.Column("fetched_at", sa.DateTime(), nullable=False),
            sa.Column("is_estimated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.UniqueConstraint("stock_id", "observation_date", name="uq_stock_obs_date"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    for name in ("stock_observations", "stocks"):
        if _table_exists(conn, name):
            op.drop_table(name)
