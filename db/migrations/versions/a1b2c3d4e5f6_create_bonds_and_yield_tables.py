"""create bonds, issuers, yield_observations

Revision ID: a1b2c3d4e5f6
Revises: c33a23e70646
Create Date: 2026-08-10

Fase 1: DJPPR pipeline stores auction results as bond metadata + yield
observations. Tables follow SCHEMA.md. On DBs where they already exist
(bootstrap DDL), keep them; otherwise create.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'c33a23e70646'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "issuers"):
        op.create_table(
            "issuers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("sector", sa.String(length=100), nullable=False),
            sa.Column("ticker", sa.String(length=20), nullable=True),
        )
    if not _table_exists(conn, "bonds"):
        op.create_table(
            "bonds",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(length=30), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("type", sa.String(length=30), nullable=False),
            sa.Column("issuer_id", sa.Integer(), sa.ForeignKey("issuers.id"), nullable=True),
            sa.Column("coupon_rate", sa.Numeric(precision=6, scale=4), nullable=True),
            sa.Column("issue_date", sa.Date(), nullable=True),
            sa.Column("maturity_date", sa.Date(), nullable=True),
            sa.Column("tenor_years", sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.UniqueConstraint("code", name="uq_bonds_code"),
        )
    if not _table_exists(conn, "yield_observations"):
        op.create_table(
            "yield_observations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("bond_id", sa.Integer(), sa.ForeignKey("bonds.id"), nullable=False),
            sa.Column("observation_date", sa.Date(), nullable=False),
            sa.Column("yield_value", sa.Numeric(precision=8, scale=4), nullable=False),
            sa.Column("price", sa.Numeric(precision=12, scale=4), nullable=True),
            sa.Column("source", sa.String(length=100), nullable=False),
            sa.Column("fetched_at", sa.DateTime(), nullable=False),
            sa.Column("is_estimated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.UniqueConstraint("bond_id", "observation_date", name="uq_yield_bond_date"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    for name in ("yield_observations", "bonds", "issuers"):
        if _table_exists(conn, name):
            op.drop_table(name)