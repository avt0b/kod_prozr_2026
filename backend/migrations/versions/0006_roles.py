"""User roles (citizen/analyst/admin) and authorship of citizen appeals (#70)."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Все пользователи до ролей были аналитиками.
    op.add_column(
        "users",
        sa.Column("role", sa.String(16), nullable=False, server_default="analyst"),
        schema="core",
    )
    op.create_index("ix_core_users_role", "users", ["role"], schema="core")
    # naming_convention метаданных: "role" -> ck_users_role.
    op.create_check_constraint(
        "role", "users", "role IN ('citizen', 'analyst', 'admin')", schema="core"
    )
    op.create_table(
        "citizen_appeals",
        sa.Column("appeal_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("core.users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="core",
    )
    op.create_index(
        "ix_core_citizen_appeals_user_id", "citizen_appeals", ["user_id"], schema="core"
    )


def downgrade() -> None:
    op.drop_table("citizen_appeals", schema="core")
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check", schema="core")
    op.drop_index("ix_core_users_role", "users", schema="core")
    op.drop_column("users", "role", schema="core")
