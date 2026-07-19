"""Add deterministic triage policies and recruiter dispositions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260719_0004"
down_revision: str | None = "20260719_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_POLICY = (
    '{"shortlist_fit_threshold": 80.0, "shortlist_evidence_threshold": 80.0, '
    '"require_mandatory_met": true, "require_no_clarification_flags": true}'
)


def upgrade() -> None:
    connection = op.get_bind()
    user_settings_columns = {
        item["name"] for item in sa.inspect(connection).get_columns("user_settings")
    }
    if "default_triage_policy" not in user_settings_columns:
        op.add_column(
            "user_settings",
            sa.Column(
                "default_triage_policy",
                sa.JSON(),
                nullable=False,
                server_default=DEFAULT_POLICY,
            ),
        )
    job_columns = {item["name"] for item in sa.inspect(connection).get_columns("job_descriptions")}
    if "triage_policy" not in job_columns:
        op.add_column(
            "job_descriptions",
            sa.Column("triage_policy", sa.JSON(), nullable=False, server_default=DEFAULT_POLICY),
        )
    if "triage_policy_version" not in job_columns:
        op.add_column(
            "job_descriptions",
            sa.Column("triage_policy_version", sa.Integer(), nullable=False, server_default="1"),
        )
    table_names = set(sa.inspect(connection).get_table_names())
    if "recruiter_dispositions" not in table_names:
        op.create_table(
            "recruiter_dispositions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("comparison_id", sa.String(length=36), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("reason_code", sa.String(length=80), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("assigned_recruiter", sa.String(length=200), nullable=True),
            sa.Column("triage_suggestion_snapshot", sa.String(length=60), nullable=False),
            sa.Column("triage_policy_snapshot", sa.JSON(), nullable=False),
            sa.Column("triage_policy_version", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["comparison_id"], ["comparisons.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("comparison_id"),
        )
    disposition_indexes = {
        item["name"] for item in sa.inspect(connection).get_indexes("recruiter_dispositions")
    }
    if "ix_recruiter_dispositions_comparison_id" not in disposition_indexes:
        op.create_index(
            "ix_recruiter_dispositions_comparison_id",
            "recruiter_dispositions",
            ["comparison_id"],
        )
    if "ix_recruiter_dispositions_status" not in disposition_indexes:
        op.create_index(
            "ix_recruiter_dispositions_status",
            "recruiter_dispositions",
            ["status"],
        )
    if "recruiter_disposition_events" not in table_names:
        op.create_table(
            "recruiter_disposition_events",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("disposition_id", sa.String(length=36), nullable=False),
            sa.Column("previous_status", sa.String(length=40), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("reason_code", sa.String(length=80), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("assigned_recruiter", sa.String(length=200), nullable=True),
            sa.Column("triage_suggestion_snapshot", sa.String(length=60), nullable=False),
            sa.Column("triage_policy_snapshot", sa.JSON(), nullable=False),
            sa.Column("triage_policy_version", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["disposition_id"], ["recruiter_dispositions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    event_indexes = {
        item["name"] for item in sa.inspect(connection).get_indexes("recruiter_disposition_events")
    }
    if "ix_recruiter_disposition_events_disposition_id" not in event_indexes:
        op.create_index(
            "ix_recruiter_disposition_events_disposition_id",
            "recruiter_disposition_events",
            ["disposition_id"],
        )


def downgrade() -> None:
    op.drop_index(
        "ix_recruiter_disposition_events_disposition_id",
        table_name="recruiter_disposition_events",
    )
    op.drop_table("recruiter_disposition_events")
    op.drop_index("ix_recruiter_dispositions_status", table_name="recruiter_dispositions")
    op.drop_index("ix_recruiter_dispositions_comparison_id", table_name="recruiter_dispositions")
    op.drop_table("recruiter_dispositions")
    op.drop_column("job_descriptions", "triage_policy_version")
    op.drop_column("job_descriptions", "triage_policy")
    op.drop_column("user_settings", "default_triage_policy")
