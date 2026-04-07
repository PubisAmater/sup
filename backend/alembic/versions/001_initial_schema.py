"""Initial schema with RLS

Revision ID: 001
Revises:
Create Date: 2026-04-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), unique=True, nullable=False),
        sa.Column("username", sa.String(255)),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255)),
        sa.Column("role", sa.String(50), server_default="line"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    # Employees
    op.create_table(
        "employees",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), unique=True),
        sa.Column("position", sa.String(255), nullable=False),
        sa.Column("department", sa.String(255), nullable=False),
        sa.Column("hired_at", sa.Date()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_employees_tenant_id", "employees", ["tenant_id"])

    # Meetings
    op.create_table(
        "meetings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("scheduled_at", sa.DateTime()),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("organizer_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(50), server_default="scheduled"),
        sa.Column("transcript", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_meetings_tenant_id", "meetings", ["tenant_id"])

    # Decisions
    op.create_table(
        "decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("decided_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_decisions_tenant_id", "decisions", ["tenant_id"])
    op.create_index("ix_decisions_meeting_id", "decisions", ["meeting_id"])

    # Tasks
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("assignee_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id")),
        sa.Column("decision_id", sa.Uuid(), sa.ForeignKey("decisions.id")),
        sa.Column("status", sa.String(50), server_default="todo"),
        sa.Column("priority", sa.String(50), server_default="medium"),
        sa.Column("due_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"])
    op.create_index("ix_tasks_assignee_id", "tasks", ["assignee_id"])

    # Row Level Security policies
    rls_tables = ["users", "employees", "meetings", "decisions", "tasks"]
    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{table} ON {table} "
            f"USING (tenant_id::text = current_setting('app.current_tenant', TRUE))"
        )
        # Allow superadmin bypass (when app.current_tenant is not set)
        op.execute(
            f"CREATE POLICY superadmin_bypass_{table} ON {table} "
            f"USING (current_setting('app.current_tenant', TRUE) IS NULL "
            f"OR current_setting('app.current_tenant', TRUE) = '')"
        )


def downgrade() -> None:
    rls_tables = ["tasks", "decisions", "meetings", "employees", "users"]
    for table in rls_tables:
        op.execute(f"DROP POLICY IF EXISTS superadmin_bypass_{table} ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("tasks")
    op.drop_table("decisions")
    op.drop_table("meetings")
    op.drop_table("employees")
    op.drop_table("users")
    op.drop_table("tenants")
