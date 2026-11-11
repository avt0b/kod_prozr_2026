from collections.abc import Iterator, Sequence

# Длинный IN (...) упирается в лимит параметров asyncpg (32767) — режем списки id.
IN_CHUNK = 5000


def chunked[T](items: Sequence[T], size: int = IN_CHUNK) -> Iterator[Sequence[T]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
