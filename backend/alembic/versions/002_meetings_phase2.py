"""Meetings phase 2: processing status, participants, decision fields

Revision ID: 002
Revises: 001
Create Date: 2026-04-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Meetings: add processing fields and notion sync
    op.add_column("meetings", sa.Column("processing_status", sa.String(50), server_default="pending"))
    op.add_column("meetings", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column("meetings", sa.Column("notion_page_id", sa.String(255), nullable=True))
    op.add_column("meetings", sa.Column("raw_transcript_url", sa.String(1000), nullable=True))

    # Decisions: add assignee, due_date, priority, notion sync
    op.add_column("decisions", sa.Column("assignee_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("decisions", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column("decisions", sa.Column("priority", sa.String(50), server_default="medium"))
    op.add_column("decisions", sa.Column("notion_page_id", sa.String(255), nullable=True))

    # Tasks: add notion sync
    op.add_column("tasks", sa.Column("notion_page_id", sa.String(255), nullable=True))

    # Meeting participants (M2M)
    op.create_table(
        "meeting_participants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_in_meeting", sa.String(50), server_default="participant"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_meeting_participants_tenant_id", "meeting_participants", ["tenant_id"])
    op.create_index("ix_meeting_participants_meeting_id", "meeting_participants", ["meeting_id"])
    op.create_index("ix_meeting_participants_user_id", "meeting_participants", ["user_id"])

    # RLS for meeting_participants
    op.execute("ALTER TABLE meeting_participants ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation_meeting_participants ON meeting_participants "
        "USING (tenant_id::text = current_setting('app.current_tenant', TRUE))"
    )
    op.execute(
        "CREATE POLICY superadmin_bypass_meeting_participants ON meeting_participants "
        "USING (current_setting('app.current_tenant', TRUE) IS NULL "
        "OR current_setting('app.current_tenant', TRUE) = '')"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS superadmin_bypass_meeting_participants ON meeting_participants")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_meeting_participants ON meeting_participants")
    op.execute("ALTER TABLE meeting_participants DISABLE ROW LEVEL SECURITY")
    op.drop_table("meeting_participants")

    op.drop_column("tasks", "notion_page_id")
    op.drop_column("decisions", "notion_page_id")
    op.drop_column("decisions", "priority")
    op.drop_column("decisions", "due_date")
    op.drop_column("decisions", "assignee_id")
    op.drop_column("meetings", "raw_transcript_url")
    op.drop_column("meetings", "notion_page_id")
    op.drop_column("meetings", "processing_error")
    op.drop_column("meetings", "processing_status")
