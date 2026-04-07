"""Weekly reports

Revision ID: 003
Revises: 002
Create Date: 2026-04-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weekly_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("completed_tasks", sa.Text()),
        sa.Column("metrics_json", sa.Text()),
        sa.Column("requests", sa.Text()),
        sa.Column("attachments_json", sa.Text()),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("submitted_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_weekly_reports_tenant_id", "weekly_reports", ["tenant_id"])
    op.create_index("ix_weekly_reports_user_id", "weekly_reports", ["user_id"])

    op.execute("ALTER TABLE weekly_reports ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation_weekly_reports ON weekly_reports "
        "USING (tenant_id::text = current_setting('app.current_tenant', TRUE))"
    )
    op.execute(
        "CREATE POLICY superadmin_bypass_weekly_reports ON weekly_reports "
        "USING (current_setting('app.current_tenant', TRUE) IS NULL "
        "OR current_setting('app.current_tenant', TRUE) = '')"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS superadmin_bypass_weekly_reports ON weekly_reports")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_weekly_reports ON weekly_reports")
    op.drop_table("weekly_reports")
