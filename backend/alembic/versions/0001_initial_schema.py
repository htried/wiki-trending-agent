"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("hour", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
    )
    op.create_table(
        "raw_hourly_trends",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dt", sa.DateTime(), nullable=False),
        sa.Column("project", sa.String(length=100), nullable=False),
        sa.Column("identifier", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("absolute_views_current", sa.Integer(), nullable=False),
        sa.Column("absolute_views_zscore", sa.Float(), nullable=True),
        sa.Column("views_proportion_current", sa.Float(), nullable=False),
        sa.Column("views_proportion_zscore", sa.Float(), nullable=True),
    )
    op.create_table(
        "run_pages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("analysis_runs.id"), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("absolute_views_current", sa.Integer(), nullable=False),
        sa.Column("absolute_views_zscore", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
    )
    op.create_table(
        "page_news_hits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("analysis_runs.id"), nullable=False),
        sa.Column("page_title", sa.String(length=512), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=True),
    )
    op.create_table(
        "page_wiki_content",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("analysis_runs.id"), nullable=False),
        sa.Column("page_title", sa.String(length=512), nullable=False),
        sa.Column("revision", sa.String(length=128), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
    )
    op.create_table(
        "page_reasoning",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("analysis_runs.id"), nullable=False),
        sa.Column("page_title", sa.String(length=512), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
    )
    op.create_table(
        "run_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("analysis_runs.id"), nullable=False),
        sa.Column("event_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("run_events")
    op.drop_table("page_reasoning")
    op.drop_table("page_wiki_content")
    op.drop_table("page_news_hits")
    op.drop_table("run_pages")
    op.drop_table("raw_hourly_trends")
    op.drop_table("analysis_runs")
