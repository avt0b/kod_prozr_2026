from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import UUIDMixin
from src.modules.officials.domain.appointment import Appointment
from src.modules.officials.domain.value_objects import Period
from src.modules.officials.infrastructure.database.schema import OFFICIALS_SCHEMA


class AppointmentModel(Base, UUIDMixin):
    __tablename__ = "appointments"
    __table_args__ = {"schema": OFFICIALS_SCHEMA}

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{OFFICIALS_SCHEMA}.persons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{OFFICIALS_SCHEMA}.positions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    ended_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    def to_entity(self) -> Appointment:
        return Appointment(
            id=self.id,
            person_id=self.person_id,
            position_id=self.position_id,
            period=Period(self.started_at, self.ended_at),
        )

    @staticmethod
    def row(entity: Appointment) -> dict[str, Any]:
        return {
            "id": entity.id,
            "person_id": entity.person_id,
            "position_id": entity.position_id,
            "started_at": entity.period.started_at,
            "ended_at": entity.period.ended_at,
        }
