"""Initial schema - tenants, api_keys, access_logs

Revision ID: 0001
Revises: None
Create Date: 2026-01-04

This migration creates the initial database schema for GlassTrax Bridge.
It captures the existing model structure as of v1.0.0.

Tables:
- tenants: Organizations/applications that own API keys
- api_keys: Authentication credentials with permissions
- access_logs: Request/response audit trail
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("key_prefix", sa.String(length=12), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("rate_limit", sa.Integer(), nullable=False, default=60),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create access_logs table
    op.create_table(
        "access_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("api_key_id", sa.Integer(), nullable=True),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("key_prefix", sa.String(length=12), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("query_string", sa.String(length=1000), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_time_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for access_logs
    op.create_index("ix_access_logs_created_at", "access_logs", ["created_at"])
    op.create_index("ix_access_logs_api_key_created", "access_logs", ["api_key_id", "created_at"])
    op.create_index("ix_access_logs_tenant_created", "access_logs", ["tenant_id", "created_at"])
    op.create_index("ix_access_logs_path_created", "access_logs", ["path", "created_at"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index("ix_access_logs_path_created", table_name="access_logs")
    op.drop_index("ix_access_logs_tenant_created", table_name="access_logs")
    op.drop_index("ix_access_logs_api_key_created", table_name="access_logs")
    op.drop_index("ix_access_logs_created_at", table_name="access_logs")
    op.drop_table("access_logs")
    op.drop_table("api_keys")
    op.drop_table("tenants")
