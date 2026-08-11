"""initial macro_indicators formal schema

Revision ID: c33a23e70646
Revises:
Create Date: 2026-08-10 07:35:56.979717

This migration represents the table the way SCHEMA.md + db/models.py intend it.
On this repo the table already exists (bootstrap DDL + many environments), so
checkfirst keeps it a no-op there while still creating it on a fresh database.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c33a23e70646'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "macro_indicators"):
        return  # already present (bootstrap DDL) -- structure matches model
    op.create_table(
        "macro_indicators",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("indicator_type", sa.String(length=50), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "indicator_type", "observation_date", name="uq_macro_type_date"
        ),
    )


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "macro_indicators"):
        op.drop_table("macro_indicators")