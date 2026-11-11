from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Date, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import UUIDMixin
from src.modules.counterparties.domain.company import Company, CompanyRole
from src.modules.counterparties.domain.enums import CompanyRoleKind, CompanyStatus
from src.modules.counterparties.infrastructure.database.schema import COUNTERPARTIES_SCHEMA


class CompanyModel(Base, UUIDMixin):
    __tablename__ = "companies"
    __table_args__ = {"schema": COUNTERPARTIES_SCHEMA}

    inn: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    ogrn: Mapped[str] = mapped_column(String(15), nullable=False)
    name: Mapped[str] = mapped_column(String(1024), nullable=False)
    okved: Mapped[str] = mapped_column(String(16), nullable=False)
    address: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registered_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    def to_entity(self) -> Company:
        return Company(
            id=self.id,
            inn=self.inn,
            ogrn=self.ogrn,
            name=self.name,
            okved=self.okved,
            address=self.address,
            phone=self.phone,
            registered_at=self.registered_at,
            status=CompanyStatus(self.status),
        )

    @staticmethod
    def row(entity: Company) -> dict[str, Any]:
        return {
            "id": entity.id,
            "inn": entity.inn,
            "ogrn": entity.ogrn,
            "name": entity.name,
            "okved": entity.okved,
            "address": entity.address,
            "phone": entity.phone,
            "registered_at": entity.registered_at,
            "status": entity.status.value,
        }


class CompanyRoleModel(Base, UUIDMixin):
    __tablename__ = "company_roles"
    __table_args__ = {"schema": COUNTERPARTIES_SCHEMA}

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{COUNTERPARTIES_SCHEMA}.companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Человек живёт в контексте officials: id без внешнего ключа.
    person_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    share: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    ended_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    def to_entity(self) -> CompanyRole:
        return CompanyRole(
            id=self.id,
            company_id=self.company_id,
            person_id=self.person_id,
            role=CompanyRoleKind(self.role),
            share=self.share,
            started_at=self.started_at,
            ended_at=self.ended_at,
        )

    @staticmethod
    def row(entity: CompanyRole) -> dict[str, Any]:
        return {
            "id": entity.id,
            "company_id": entity.company_id,
            "person_id": entity.person_id,
            "role": entity.role.value,
            "share": entity.share,
            "started_at": entity.started_at,
            "ended_at": entity.ended_at,
        }
