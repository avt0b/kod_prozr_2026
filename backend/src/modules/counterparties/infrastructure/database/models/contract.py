from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import UUIDMixin
from src.modules.counterparties.domain.contract import Contract
from src.modules.counterparties.infrastructure.database.schema import COUNTERPARTIES_SCHEMA


class ContractModel(Base, UUIDMixin):
    __tablename__ = "contracts"
    __table_args__ = {"schema": COUNTERPARTIES_SCHEMA}

    reg_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Орган живёт в контексте officials: id без внешнего ключа.
    customer_organ_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    supplier_company_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{COUNTERPARTIES_SCHEMA}.companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    signed_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    okpd2: Mapped[str | None] = mapped_column(String(32), nullable=True)
    method: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def to_entity(self) -> Contract:
        return Contract(
            id=self.id,
            reg_number=self.reg_number,
            customer_organ_id=self.customer_organ_id,
            supplier_company_id=self.supplier_company_id,
            amount=float(self.amount),
            signed_at=self.signed_at,
            okpd2=self.okpd2,
            method=self.method,
        )

    @staticmethod
    def row(entity: Contract) -> dict[str, Any]:
        return {
            "id": entity.id,
            "reg_number": entity.reg_number,
            "customer_organ_id": entity.customer_organ_id,
            "supplier_company_id": entity.supplier_company_id,
            "amount": Decimal(str(entity.amount)),
            "signed_at": entity.signed_at,
            "okpd2": entity.okpd2,
            "method": entity.method,
        }
