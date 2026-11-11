from collections.abc import Sequence
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

# asyncpg ограничивает число параметров запроса (32767) — режем на пачки.
UPSERT_CHUNK = 1000


async def upsert_rows(
    session: AsyncSession, model: type[DeclarativeBase], rows: Sequence[dict[str, Any]]
) -> None:
    """INSERT ... ON CONFLICT (id) DO UPDATE для пачки строк. Не коммитит."""
    if not rows:
        return
    columns = model.__table__.columns
    for start in range(0, len(rows), UPSERT_CHUNK):
        chunk = list(rows[start : start + UPSERT_CHUNK])
        stmt = pg_insert(model).values(chunk)
        update_columns = {
            column.name: stmt.excluded[column.name]
            for column in columns
            if column.name in chunk[0] and column.name != "id"
        }
        if update_columns:
            stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_columns)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
        await session.execute(stmt)
