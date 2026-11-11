"""initial context schemas

Одна схема Postgres на bounded context (как в optimus): officials, counterparties, risk,
appeals, reports. В public — только alembic_version. Внешних ключей между контекстами нет:
чужие id (employments.company_id, company_roles.person_id, contracts.customer_organ_id,
risk.*.person_id, appeals.linked_person_ids, report_drafts.person_id) хранятся без FK.

Revision ID: 0001
Revises:
Create Date: 2026-11-11 09:01:56.918315

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = ("officials", "counterparties", "risk", "appeals", "reports")


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    op.create_table(
        "appeals",
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("is_corruption", sa.Boolean(), nullable=True),
        sa.Column(
            "linked_person_ids", postgresql.ARRAY(sa.Uuid()), server_default="{}", nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appeals")),
        schema="appeals",
    )
    op.create_index(
        op.f("ix_appeals_category"), "appeals", ["category"], unique=False, schema="appeals"
    )
    op.create_index(
        "ix_appeals_linked_person_ids",
        "appeals",
        ["linked_person_ids"],
        unique=False,
        schema="appeals",
        postgresql_using="gin",
    )
    op.create_index(
        op.f("ix_appeals_received_at"), "appeals", ["received_at"], unique=False, schema="appeals"
    )
    op.create_index(
        op.f("ix_appeals_status"), "appeals", ["status"], unique=False, schema="appeals"
    )
    op.create_table(
        "companies",
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column("ogrn", sa.String(length=15), nullable=False),
        sa.Column("name", sa.String(length=1024), nullable=False),
        sa.Column("okved", sa.String(length=16), nullable=False),
        sa.Column("address", sa.String(length=1024), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("registered_at", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
        schema="counterparties",
    )
    op.create_index(
        op.f("ix_companies_inn"), "companies", ["inn"], unique=False, schema="counterparties"
    )
    op.create_table(
        "organs",
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column("region", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organs")),
        schema="officials",
    )
    op.create_index(op.f("ix_organs_inn"), "organs", ["inn"], unique=False, schema="officials")
    op.create_index(
        op.f("ix_organs_region"), "organs", ["region"], unique=False, schema="officials"
    )
    op.create_table(
        "persons",
        sa.Column("full_name", sa.String(length=512), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("address", sa.String(length=1024), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_persons")),
        schema="officials",
    )
    op.create_index(
        "ix_persons_full_name", "persons", ["full_name"], unique=False, schema="officials"
    )
    op.create_index(op.f("ix_persons_inn"), "persons", ["inn"], unique=False, schema="officials")
    op.create_table(
        "report_drafts",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("generator", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_drafts")),
        schema="reports",
    )
    op.create_index(
        op.f("ix_report_drafts_person_id"),
        "report_drafts",
        ["person_id"],
        unique=False,
        schema="reports",
    )
    op.create_table(
        "flags",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("rule_code", sa.String(length=8), nullable=False),
        sa.Column("rule_name", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("legal_ref", sa.String(length=255), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_flags")),
        schema="risk",
    )
    op.create_index(op.f("ix_flags_person_id"), "flags", ["person_id"], unique=False, schema="risk")
    op.create_index(op.f("ix_flags_rule_code"), "flags", ["rule_code"], unique=False, schema="risk")
    op.create_index(op.f("ix_flags_severity"), "flags", ["severity"], unique=False, schema="risk")
    op.create_table(
        "scores",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("flags_count", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("person_id", name=op.f("pk_scores")),
        schema="risk",
    )
    op.create_index(op.f("ix_scores_score"), "scores", ["score"], unique=False, schema="risk")
    op.create_table(
        "company_roles",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("share", sa.Float(), nullable=True),
        sa.Column("started_at", sa.Date(), nullable=False),
        sa.Column("ended_at", sa.Date(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["counterparties.companies.id"],
            name=op.f("fk_company_roles_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_roles")),
        schema="counterparties",
    )
    op.create_index(
        op.f("ix_company_roles_company_id"),
        "company_roles",
        ["company_id"],
        unique=False,
        schema="counterparties",
    )
    op.create_index(
        op.f("ix_company_roles_person_id"),
        "company_roles",
        ["person_id"],
        unique=False,
        schema="counterparties",
    )
    op.create_table(
        "contracts",
        sa.Column("reg_number", sa.String(length=64), nullable=False),
        sa.Column("customer_organ_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_company_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("signed_at", sa.Date(), nullable=False),
        sa.Column("okpd2", sa.String(length=32), nullable=True),
        sa.Column("method", sa.String(length=64), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["supplier_company_id"],
            ["counterparties.companies.id"],
            name=op.f("fk_contracts_supplier_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contracts")),
        schema="counterparties",
    )
    op.create_index(
        op.f("ix_contracts_customer_organ_id"),
        "contracts",
        ["customer_organ_id"],
        unique=False,
        schema="counterparties",
    )
    op.create_index(
        op.f("ix_contracts_reg_number"),
        "contracts",
        ["reg_number"],
        unique=False,
        schema="counterparties",
    )
    op.create_index(
        op.f("ix_contracts_signed_at"),
        "contracts",
        ["signed_at"],
        unique=False,
        schema="counterparties",
    )
    op.create_index(
        op.f("ix_contracts_supplier_company_id"),
        "contracts",
        ["supplier_company_id"],
        unique=False,
        schema="counterparties",
    )
    op.create_table(
        "employments",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.Date(), nullable=False),
        sa.Column("ended_at", sa.Date(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["officials.persons.id"],
            name=op.f("fk_employments_person_id_persons"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employments")),
        schema="officials",
    )
    op.create_index(
        op.f("ix_employments_company_id"),
        "employments",
        ["company_id"],
        unique=False,
        schema="officials",
    )
    op.create_index(
        op.f("ix_employments_person_id"),
        "employments",
        ["person_id"],
        unique=False,
        schema="officials",
    )
    op.create_table(
        "kinships",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("relative_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["officials.persons.id"],
            name=op.f("fk_kinships_person_id_persons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["relative_id"],
            ["officials.persons.id"],
            name=op.f("fk_kinships_relative_id_persons"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kinships")),
        schema="officials",
    )
    op.create_index(
        op.f("ix_kinships_person_id"), "kinships", ["person_id"], unique=False, schema="officials"
    )
    op.create_index(
        op.f("ix_kinships_relative_id"),
        "kinships",
        ["relative_id"],
        unique=False,
        schema="officials",
    )
    op.create_table(
        "positions",
        sa.Column("organ_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("department", sa.String(length=512), nullable=False),
        sa.Column("is_corruption_risky", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organ_id"],
            ["officials.organs.id"],
            name=op.f("fk_positions_organ_id_organs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_positions")),
        schema="officials",
    )
    op.create_index(
        op.f("ix_positions_organ_id"), "positions", ["organ_id"], unique=False, schema="officials"
    )
    op.create_table(
        "appointments",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.Date(), nullable=False),
        sa.Column("ended_at", sa.Date(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["officials.persons.id"],
            name=op.f("fk_appointments_person_id_persons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["officials.positions.id"],
            name=op.f("fk_appointments_position_id_positions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appointments")),
        schema="officials",
    )
    op.create_index(
        op.f("ix_appointments_person_id"),
        "appointments",
        ["person_id"],
        unique=False,
        schema="officials",
    )
    op.create_index(
        op.f("ix_appointments_position_id"),
        "appointments",
        ["position_id"],
        unique=False,
        schema="officials",
    )
    op.create_table(
        "authorities",
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["officials.positions.id"],
            name=op.f("fk_authorities_position_id_positions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authorities")),
        schema="officials",
    )
    op.create_index(
        op.f("ix_authorities_kind"), "authorities", ["kind"], unique=False, schema="officials"
    )
    op.create_index(
        op.f("ix_authorities_position_id"),
        "authorities",
        ["position_id"],
        unique=False,
        schema="officials",
    )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_authorities_position_id"), table_name="authorities", schema="officials")
    op.drop_index(op.f("ix_authorities_kind"), table_name="authorities", schema="officials")
    op.drop_table("authorities", schema="officials")
    op.drop_index(
        op.f("ix_appointments_position_id"), table_name="appointments", schema="officials"
    )
    op.drop_index(op.f("ix_appointments_person_id"), table_name="appointments", schema="officials")
    op.drop_table("appointments", schema="officials")
    op.drop_index(op.f("ix_positions_organ_id"), table_name="positions", schema="officials")
    op.drop_table("positions", schema="officials")
    op.drop_index(op.f("ix_kinships_relative_id"), table_name="kinships", schema="officials")
    op.drop_index(op.f("ix_kinships_person_id"), table_name="kinships", schema="officials")
    op.drop_table("kinships", schema="officials")
    op.drop_index(op.f("ix_employments_person_id"), table_name="employments", schema="officials")
    op.drop_index(op.f("ix_employments_company_id"), table_name="employments", schema="officials")
    op.drop_table("employments", schema="officials")
    op.drop_index(
        op.f("ix_contracts_supplier_company_id"), table_name="contracts", schema="counterparties"
    )
    op.drop_index(op.f("ix_contracts_signed_at"), table_name="contracts", schema="counterparties")
    op.drop_index(op.f("ix_contracts_reg_number"), table_name="contracts", schema="counterparties")
    op.drop_index(
        op.f("ix_contracts_customer_organ_id"), table_name="contracts", schema="counterparties"
    )
    op.drop_table("contracts", schema="counterparties")
    op.drop_index(
        op.f("ix_company_roles_person_id"), table_name="company_roles", schema="counterparties"
    )
    op.drop_index(
        op.f("ix_company_roles_company_id"), table_name="company_roles", schema="counterparties"
    )
    op.drop_table("company_roles", schema="counterparties")
    op.drop_index(op.f("ix_scores_score"), table_name="scores", schema="risk")
    op.drop_table("scores", schema="risk")
    op.drop_index(op.f("ix_flags_severity"), table_name="flags", schema="risk")
    op.drop_index(op.f("ix_flags_rule_code"), table_name="flags", schema="risk")
    op.drop_index(op.f("ix_flags_person_id"), table_name="flags", schema="risk")
    op.drop_table("flags", schema="risk")
    op.drop_index(op.f("ix_report_drafts_person_id"), table_name="report_drafts", schema="reports")
    op.drop_table("report_drafts", schema="reports")
    op.drop_index(op.f("ix_persons_inn"), table_name="persons", schema="officials")
    op.drop_index("ix_persons_full_name", table_name="persons", schema="officials")
    op.drop_table("persons", schema="officials")
    op.drop_index(op.f("ix_organs_region"), table_name="organs", schema="officials")
    op.drop_index(op.f("ix_organs_inn"), table_name="organs", schema="officials")
    op.drop_table("organs", schema="officials")
    op.drop_index(op.f("ix_companies_inn"), table_name="companies", schema="counterparties")
    op.drop_table("companies", schema="counterparties")
    op.drop_index(op.f("ix_appeals_status"), table_name="appeals", schema="appeals")
    op.drop_index(op.f("ix_appeals_received_at"), table_name="appeals", schema="appeals")
    op.drop_index(
        "ix_appeals_linked_person_ids",
        table_name="appeals",
        schema="appeals",
        postgresql_using="gin",
    )
    op.drop_index(op.f("ix_appeals_category"), table_name="appeals", schema="appeals")
    op.drop_table("appeals", schema="appeals")
    for schema in reversed(SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema}")
