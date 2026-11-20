"""Users and revocable browser sessions."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        schema="core",
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("core.users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("refresh_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("logout_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        schema="core",
    )


def downgrade() -> None:
    op.drop_table("auth_sessions", schema="core")
    op.drop_table("users", schema="core")
