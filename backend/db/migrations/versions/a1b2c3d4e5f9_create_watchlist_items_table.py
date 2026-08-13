"""create watchlist_items table

Revision ID: a1b2c3d4e5f9
Revises: a1b2c3d4e5f8
Create Date: 2026-08-12

Fase 4: watchlist feature -- users save bonds/stocks for quick access.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f9'
down_revision: Union[str, None] = 'a1b2c3d4e5f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "watchlist_items"):
        op.create_table(
            "watchlist_items",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("item_type", sa.String(length=10), nullable=False),
            sa.Column("item_code", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "item_type", "item_code", name="uq_watchlist_user_item"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "watchlist_items"):
        op.drop_table("watchlist_items")
