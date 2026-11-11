from dataclasses import dataclass

MAX_PAGE_LIMIT = 200


@dataclass(frozen=True)
class PageRequest:
    """Пагинация для use case и репозиториев. Верхний лимит жёсткий."""

    limit: int = 20
    offset: int = 0

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= MAX_PAGE_LIMIT:
            raise ValueError(f"limit must be in 1..{MAX_PAGE_LIMIT}")
        if self.offset < 0:
            raise ValueError("offset must be >= 0")


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    total: int
