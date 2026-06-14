"""add custom fields support

Revision ID: b2c4d6e8f0a1
Revises: 9f7e2c4b1a6d
Create Date: 2026-03-14 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "b2c4d6e8f0a1"
down_revision = "9f7e2c4b1a6d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contacts",
        sa.Column("custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "accounts",
        sa.Column("custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "opportunities",
        sa.Column("custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "custom_field_definitions",
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("key", sa.String(length=150), nullable=False),
        sa.Column("field_type", sa.String(length=30), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("show_in_forms", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("show_in_details", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_in_filters", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allow_in_reports", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "critical_report_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "key", name="uq_custom_field_entity_key"),
    )
    op.create_index(
        op.f("ix_custom_field_definitions_entity_type"),
        "custom_field_definitions",
        ["entity_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_custom_field_definitions_entity_type"),
        table_name="custom_field_definitions",
    )
    op.drop_table("custom_field_definitions")
    op.drop_column("opportunities", "custom_fields")
    op.drop_column("accounts", "custom_fields")
    op.drop_column("contacts", "custom_fields")
