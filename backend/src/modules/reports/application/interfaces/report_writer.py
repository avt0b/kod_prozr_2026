from dataclasses import dataclass
from typing import Protocol

from src.modules.reports.domain.dossier import Dossier


@dataclass(frozen=True)
class WrittenReport:
    text: str
    generator: str


class ReportWriterInterface(Protocol):
    """Порт «написать текст докладной по досье». Адаптеры: шаблон (без LLM), LLM,
    фоллбэк «LLM, при сбое — шаблон»."""

    async def write(self, dossier: Dossier) -> WrittenReport: ...
