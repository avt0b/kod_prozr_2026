"""Index for supplier/customer graph lookups."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_contracts_supplier_customer",
        "contracts",
        ["supplier_company_id", "customer_organ_id"],
        schema="counterparties",
    )


def downgrade() -> None:
    op.drop_index("ix_contracts_supplier_customer", table_name="contracts", schema="counterparties")
