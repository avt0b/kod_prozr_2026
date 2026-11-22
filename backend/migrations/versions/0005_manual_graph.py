"""Analyst-owned graph overlays and explicit read shares."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA manual_graph")
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("core.users.id"), nullable=False),
        sa.Column("official_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="manual_graph",
    )
    op.create_index("ix_workspaces_official", "workspaces", ["official_id"], schema="manual_graph")
    for name in ("nodes", "edges"):
        columns = [
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.Uuid(),
                sa.ForeignKey("manual_graph.workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("label", sa.String(200 if name == "nodes" else 160), nullable=False),
            sa.Column("notes", sa.String(2000), nullable=False),
            sa.Column("source", sa.String(500), nullable=False),
        ]
        if name == "nodes":
            columns.append(sa.Column("kind", sa.String(20), nullable=False))
        else:
            columns.extend(
                [
                    sa.Column("source_id", sa.Uuid(), nullable=False),
                    sa.Column("target_id", sa.Uuid(), nullable=False),
                ]
            )
        op.create_table(name, *columns, schema="manual_graph")
        op.create_index(
            f"ix_manual_graph_{name}_workspace_id", name, ["workspace_id"], schema="manual_graph"
        )
    op.create_table(
        "shares",
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("manual_graph.workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("core.users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        schema="manual_graph",
    )


def downgrade() -> None:
    for name in ("shares", "edges", "nodes", "workspaces"):
        op.drop_table(name, schema="manual_graph")
    op.execute("DROP SCHEMA manual_graph")
