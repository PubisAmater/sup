"""Score entries and peer reviews

Revision ID: 005
Revises: 004
Create Date: 2026-04-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "score_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("score_type", sa.String(100), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("granted_by", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_score_entries_tenant_id", "score_entries", ["tenant_id"])
    op.create_index("ix_score_entries_user_id", "score_entries", ["user_id"])

    op.create_table(
        "peer_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewee_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_peer_reviews_tenant_id", "peer_reviews", ["tenant_id"])
    op.create_index("ix_peer_reviews_reviewer_id", "peer_reviews", ["reviewer_id"])
    op.create_index("ix_peer_reviews_reviewee_id", "peer_reviews", ["reviewee_id"])

    for table in ["score_entries", "peer_reviews"]:
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
    for table in ["peer_reviews", "score_entries"]:
        op.execute(f"DROP POLICY IF EXISTS superadmin_bypass_{table} ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
    op.drop_table("peer_reviews")
    op.drop_table("score_entries")
