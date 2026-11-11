from typing import Any

from sqlalchemy import Connection, MetaData, event
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.schema import CreateSchema

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


@event.listens_for(Base.metadata, "before_create")
def _create_schemas(target: MetaData, connection: Connection, **kw: Any) -> None:
    """metadata.create_all (тесты) сам создаёт схемы контекстов. В проде схемы делает Alembic."""
    for schema in sorted({table.schema for table in target.tables.values() if table.schema}):
        connection.execute(CreateSchema(schema, if_not_exists=True))
