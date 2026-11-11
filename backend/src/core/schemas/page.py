from pydantic import BaseModel


class PageResponse[T](BaseModel):
    """Единый формат списков из контракта: `{items, total}`."""

    items: list[T]
    total: int
