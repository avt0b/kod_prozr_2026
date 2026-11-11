from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import UUIDMixin
from src.modules.officials.domain.enums import AuthorityKind
from src.modules.officials.domain.organ import Authority, Organ, Position
from src.modules.officials.domain.value_objects import AuthorityScope
from src.modules.officials.infrastructure.database.schema import OFFICIALS_SCHEMA


class OrganModel(Base, UUIDMixin):
    __tablename__ = "organs"
    __table_args__ = {"schema": OFFICIALS_SCHEMA}

    name: Mapped[str] = mapped_column(String(512), nullable=False)
    inn: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    def to_entity(self) -> Organ:
        return Organ(id=self.id, name=self.name, inn=self.inn, region=self.region)

    @staticmethod
    def row(entity: Organ) -> dict[str, Any]:
        return {"id": entity.id, "name": entity.name, "inn": entity.inn, "region": entity.region}


class PositionModel(Base, UUIDMixin):
    __tablename__ = "positions"
    __table_args__ = {"schema": OFFICIALS_SCHEMA}

    organ_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{OFFICIALS_SCHEMA}.organs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    department: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    is_corruption_risky: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def to_entity(self) -> Position:
        return Position(
            id=self.id,
            organ_id=self.organ_id,
            title=self.title,
            department=self.department,
            is_corruption_risky=self.is_corruption_risky,
        )

    @staticmethod
    def row(entity: Position) -> dict[str, Any]:
        return {
            "id": entity.id,
            "organ_id": entity.organ_id,
            "title": entity.title,
            "department": entity.department,
            "is_corruption_risky": entity.is_corruption_risky,
        }


class AuthorityModel(Base, UUIDMixin):
    __tablename__ = "authorities"
    __table_args__ = {"schema": OFFICIALS_SCHEMA}

    position_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{OFFICIALS_SCHEMA}.positions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # {"okpd2": [...], "okved": [...], "territory": "..."}
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    def to_entity(self) -> Authority:
        scope = self.scope or {}
        return Authority(
            id=self.id,
            position_id=self.position_id,
            kind=AuthorityKind(self.kind),
            scope=AuthorityScope(
                okpd2=tuple(scope.get("okpd2") or ()),
                okved=tuple(scope.get("okved") or ()),
                territory=scope.get("territory"),
            ),
        )

    @staticmethod
    def row(entity: Authority) -> dict[str, Any]:
        return {
            "id": entity.id,
            "position_id": entity.position_id,
            "kind": entity.kind.value,
            "scope": {
                "okpd2": list(entity.scope.okpd2),
                "okved": list(entity.scope.okved),
                "territory": entity.scope.territory,
            },
        }
