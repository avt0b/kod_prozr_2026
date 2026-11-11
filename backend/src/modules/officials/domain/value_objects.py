from dataclasses import dataclass, field
from datetime import date

from src.modules.officials.domain.exceptions import InvalidPeriodError


@dataclass(frozen=True)
class Period:
    """Период действия: замещение должности, работа, родство не ограничено во времени."""

    started_at: date
    ended_at: date | None = None

    def __post_init__(self) -> None:
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise InvalidPeriodError()

    def contains(self, day: date) -> bool:
        return self.started_at <= day and (self.ended_at is None or day <= self.ended_at)

    def is_active(self, today: date) -> bool:
        return self.contains(today)


@dataclass(frozen=True)
class AuthorityScope:
    """Сфера полномочий: коды ОКПД2/ОКВЭД и территория.

    JSON-форма (контракт уточнён): {"okpd2": ["41.20"], "okved": ["41.2"], "territory": "..."}.
    Пустой список кодов = полномочия на любые коды.
    """

    okpd2: tuple[str, ...] = field(default_factory=tuple)
    okved: tuple[str, ...] = field(default_factory=tuple)
    territory: str | None = None

    def covers_okpd2(self, code: str | None) -> bool:
        if not self.okpd2 or code is None:
            return True
        return any(code.startswith(prefix) for prefix in self.okpd2)
