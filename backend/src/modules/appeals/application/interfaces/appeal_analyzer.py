from typing import Protocol

from src.modules.appeals.domain.analysis import AppealAnalysis


class AppealAnalyzer(Protocol):
    """Порт анализа обращения (имя из docs/contracts.md).

    Реализации — infrastructure/adapters: LLM (OpenAI-совместимый API), правила/регэкспы
    (работает без LLM) и фоллбэк «LLM, при сбое — правила». Выбор — в presentation/dependencies.
    """

    async def analyze(self, text: str) -> AppealAnalysis:
        """Классификация, сущности, сигналы, конкретность, маршрут. Сбой LLM —
        ExternalServiceError (фоллбэк-адаптер его перехватывает)."""
        ...
