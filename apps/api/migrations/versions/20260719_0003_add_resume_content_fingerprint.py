"""Add normalized content fingerprints to resume versions."""

from collections.abc import Sequence
from hashlib import sha256

import sqlalchemy as sa
from alembic import op

revision: str = "20260719_0003"
down_revision: str | None = "20260719_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _content_fingerprint(raw_text: str) -> str:
    normalized = " ".join(raw_text.split()).casefold()
    return sha256(normalized.encode("utf-8")).hexdigest()


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {item["name"] for item in inspector.get_columns("resumes")}
    if "content_sha256" not in columns:
        op.add_column(
            "resumes",
            sa.Column("content_sha256", sa.String(length=64), nullable=True),
        )
    resumes = sa.table(
        "resumes",
        sa.column("id", sa.String(length=36)),
        sa.column("raw_text", sa.Text()),
        sa.column("content_sha256", sa.String(length=64)),
    )
    for resume_id, raw_text in connection.execute(sa.select(resumes.c.id, resumes.c.raw_text)):
        connection.execute(
            resumes.update()
            .where(resumes.c.id == resume_id)
            .values(content_sha256=_content_fingerprint(raw_text))
        )
    indexes = {item["name"] for item in sa.inspect(connection).get_indexes("resumes")}
    if "ix_resumes_content_sha256" not in indexes:
        op.create_index(
            "ix_resumes_content_sha256",
            "resumes",
            ["content_sha256"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_resumes_content_sha256", table_name="resumes")
    op.drop_column("resumes", "content_sha256")
