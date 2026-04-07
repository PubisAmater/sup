"""Metrics snapshots and alerts

Revision ID: 004
Revises: 003
Create Date: 2026-04-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("metric_name", sa.String(255), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_metric_snapshots_tenant_id", "metric_snapshots", ["tenant_id"])
    op.create_index("ix_metric_snapshots_metric_name", "metric_snapshots", ["metric_name"])
    op.create_index("ix_metric_snapshots_recorded_at", "metric_snapshots", ["recorded_at"])

    op.create_table(
        "metric_alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("metric_snapshot_id", sa.Uuid(), sa.ForeignKey("metric_snapshots.id")),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(50), server_default="info"),
        sa.Column("is_resolved", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_metric_alerts_tenant_id", "metric_alerts", ["tenant_id"])

    for table in ["metric_snapshots", "metric_alerts"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{table} ON {table} "
            f"USING (tenant_id::text = current_setting('app.current_tenant', TRUE))"
        )
        op.execute(
            f"CREATE POLICY superadmin_bypass_{table} ON {table} "
            f"USING (current_setting('app.current_tenant', TRUE) IS NULL "
            f"OR current_setting('app.current_tenant', TRUE) = '')"
        )


def downgrade() -> None:
    for table in ["metric_alerts", "metric_snapshots"]:
        op.execute(f"DROP POLICY IF EXISTS superadmin_bypass_{table} ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
    op.drop_table("metric_alerts")
    op.drop_table("metric_snapshots")
