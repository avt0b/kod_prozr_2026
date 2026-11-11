from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProblemDetails:
    """Тело ошибки API (RFC 7807, `application/problem+json`).

    title  — машинное имя ошибки (имя класса исключения), фронт может на него ветвиться;
    status — HTTP-код; detail — человекочитаемое описание; instance — путь запроса;
    errors — только для 422: список ошибок валидации полей.
    """

    title: str
    status: int
    detail: str | None = None
    type: str = "about:blank"
    instance: str | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"type": self.type, "title": self.title, "status": self.status}
        if self.detail is not None:
            result["detail"] = self.detail
        if self.instance is not None:
            result["instance"] = self.instance
        if self.errors:
            result["errors"] = self.errors
        return result
