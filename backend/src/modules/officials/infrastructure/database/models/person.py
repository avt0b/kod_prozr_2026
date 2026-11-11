from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import UUIDMixin
from src.modules.officials.domain.enums import KinshipKind
from src.modules.officials.domain.person import Employment, Kinship, Person
from src.modules.officials.domain.value_objects import Period
from src.modules.officials.infrastructure.database.schema import OFFICIALS_SCHEMA


class PersonModel(Base, UUIDMixin):
    __tablename__ = "persons"
    __table_args__ = (
        Index("ix_persons_full_name", "full_name"),
        {"schema": OFFICIALS_SCHEMA},
    )

    full_name: Mapped[str] = mapped_column(String(512), nullable=False)
    inn: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def to_entity(self) -> Person:
        return Person(
            id=self.id,
            full_name=self.full_name,
            inn=self.inn,
            birth_date=self.birth_date,
            address=self.address,
            phone=self.phone,
        )

    @staticmethod
    def row(entity: Person) -> dict[str, Any]:
        return {
            "id": entity.id,
            "full_name": entity.full_name,
            "inn": entity.inn,
            "birth_date": entity.birth_date,
            "address": entity.address,
            "phone": entity.phone,
        }


class KinshipModel(Base, UUIDMixin):
    __tablename__ = "kinships"
    __table_args__ = {"schema": OFFICIALS_SCHEMA}

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{OFFICIALS_SCHEMA}.persons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relative_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{OFFICIALS_SCHEMA}.persons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)

    def to_entity(self) -> Kinship:
        return Kinship(
            id=self.id,
            person_id=self.person_id,
            relative_id=self.relative_id,
            kind=KinshipKind(self.kind),
        )

    @staticmethod
    def row(entity: Kinship) -> dict[str, Any]:
        return {
            "id": entity.id,
            "person_id": entity.person_id,
            "relative_id": entity.relative_id,
            "kind": entity.kind.value,
        }


class EmploymentModel(Base, UUIDMixin):
    __tablename__ = "employments"
    __table_args__ = {"schema": OFFICIALS_SCHEMA}

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{OFFICIALS_SCHEMA}.persons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Компания живёт в контексте counterparties: id без внешнего ключа.
    company_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    ended_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    def to_entity(self) -> Employment:
        return Employment(
            id=self.id,
            person_id=self.person_id,
            company_id=self.company_id,
            period=Period(self.started_at, self.ended_at),
        )

    @staticmethod
    def row(entity: Employment) -> dict[str, Any]:
        return {
            "id": entity.id,
            "person_id": entity.person_id,
            "company_id": entity.company_id,
            "started_at": entity.period.started_at,
            "ended_at": entity.period.ended_at,
        }
