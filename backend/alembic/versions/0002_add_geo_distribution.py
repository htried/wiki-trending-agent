"""add geo distribution to raw hourly trends

Revision ID: 0002_add_geo_distribution
Revises: 0001_initial_schema
Create Date: 2026-03-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_geo_distribution"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("raw_hourly_trends", sa.Column("geo_distribution", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("raw_hourly_trends", "geo_distribution")
