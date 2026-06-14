"""add activities module

Revision ID: 9f7e2c4b1a6d
Revises: f6ffe9c3a85e
Create Date: 2026-03-14 17:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f7e2c4b1a6d"
down_revision: Union[str, None] = "f6ffe9c3a85e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_types",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activity_types_name"), "activity_types", ["name"], unique=True)

    op.create_table(
        "activities",
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("activity_type_id", sa.UUID(), nullable=False),
        sa.Column("contact_id", sa.UUID(), nullable=True),
        sa.Column("account_id", sa.UUID(), nullable=True),
        sa.Column("opportunity_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["activity_type_id"], ["activity_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activities_account_id"), "activities", ["account_id"], unique=False)
    op.create_index(op.f("ix_activities_completed_at"), "activities", ["completed_at"], unique=False)
    op.create_index(op.f("ix_activities_contact_id"), "activities", ["contact_id"], unique=False)
    op.create_index(op.f("ix_activities_due_at"), "activities", ["due_at"], unique=False)
    op.create_index(op.f("ix_activities_kind"), "activities", ["kind"], unique=False)
    op.create_index(op.f("ix_activities_opportunity_id"), "activities", ["opportunity_id"], unique=False)
    op.create_index(op.f("ix_activities_owner_id"), "activities", ["owner_id"], unique=False)
    op.create_index(op.f("ix_activities_priority"), "activities", ["priority"], unique=False)
    op.create_index(op.f("ix_activities_scheduled_at"), "activities", ["scheduled_at"], unique=False)
    op.create_index(op.f("ix_activities_status"), "activities", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_activities_status"), table_name="activities")
    op.drop_index(op.f("ix_activities_scheduled_at"), table_name="activities")
    op.drop_index(op.f("ix_activities_priority"), table_name="activities")
    op.drop_index(op.f("ix_activities_owner_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_opportunity_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_kind"), table_name="activities")
    op.drop_index(op.f("ix_activities_due_at"), table_name="activities")
    op.drop_index(op.f("ix_activities_contact_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_completed_at"), table_name="activities")
    op.drop_index(op.f("ix_activities_account_id"), table_name="activities")
    op.drop_table("activities")
    op.drop_index(op.f("ix_activity_types_name"), table_name="activity_types")
    op.drop_table("activity_types")
