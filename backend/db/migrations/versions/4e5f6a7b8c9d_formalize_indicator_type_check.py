"""Add a CHECK constraint to macro_indicators.indicator_type.

Instead of a formal PostgreSQL ENUM (which requires table ownership to ALTER),
this migration adds a CHECK constraint to the existing VARCHAR(50) column,
preventing typos while keeping the DDL simple and reversible.

Existing values in the DB are safe: all 3 (inflation_yoy, bi_7drr, usd_idr)
are included in the constraint list, plus the 4 new ones (pdb_yoy, tpt,
trade_balance, foreign_reserves).

Revision ID: 4e5f6a7b8c9d
Revises: a1b2c3d4e5f9
"""
from typing import Sequence, Union

from alembic import op


revision: str = "4e5f6a7b8c9d"
down_revision: Union[str, None] = "a1b2c3d4e5f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "ck_macro_indicator_type"
ALLOWED = (
    "inflation_yoy",
    "bi_7drr",
    "usd_idr",
    "pdb_yoy",
    "tpt",
    "trade_balance",
    "foreign_reserves",
)


def upgrade() -> None:
    values = ", ".join(repr(v) for v in ALLOWED)
    op.execute(
        f"ALTER TABLE macro_indicators "
        f"ADD CONSTRAINT {CONSTRAINT_NAME} "
        f"CHECK (indicator_type IN ({values}))"
    )


def downgrade() -> None:
    op.execute(
        f"ALTER TABLE macro_indicators DROP CONSTRAINT {CONSTRAINT_NAME}"
    )
