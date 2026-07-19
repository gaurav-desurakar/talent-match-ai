"""Add company-assigned identifiers to saved jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260719_0002"
down_revision: str | None = "20260717_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {item["name"] for item in inspector.get_columns("job_descriptions")}
    if "external_job_id" not in columns:
        op.add_column(
            "job_descriptions",
            sa.Column("external_job_id", sa.String(length=100), nullable=True),
        )
    indexes = {item["name"] for item in sa.inspect(connection).get_indexes("job_descriptions")}
    if "ix_job_descriptions_external_job_id" not in indexes:
        op.create_index(
            "ix_job_descriptions_external_job_id",
            "job_descriptions",
            ["external_job_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_job_descriptions_external_job_id", table_name="job_descriptions")
    op.drop_column("job_descriptions", "external_job_id")
