"""Анализ обращения через LLM (OpenAI-совместимый API) по порту LLMClientInterface из core.

Промпт — черновик: финальную версию с few-shot ведёт Влад О. (docs/ai.md). Ответ всегда
валидируется схемой; при невалидном JSON — один повтор, затем ExternalServiceError
(его перехватывает FallbackAppealAnalyzer и уходит в правила).
"""

from pydantic import ValidationError

from src.core.exceptions import ExternalServiceError
from src.core.infrastructure.interfaces.llm_client import ChatMessage, LLMClientInterface
from src.core.infrastructure.logger import get_logger
from src.modules.appeals.domain.analysis import CORRUPTION_ROUTE, GENERAL_ROUTE, AppealAnalysis
from src.modules.appeals.infrastructure.serialization import AnalysisSchema

logger = get_logger(__name__)

MAX_ATTEMPTS = 2  # ADR-05: один повтор

SYSTEM_PROMPT = f"""Ты — аналитик подразделения по профилактике коррупционных правонарушений.
Разбери обращение гражданина и верни ТОЛЬКО JSON-объект без пояснений:
{{
  "is_corruption": true|false,
  "category": "bribe" | "conflict_of_interest" | "procurement" | "abuse_of_power" | "other",
  "confidence": число 0..1,
  "entities": [{{"type": "person|organization|position|money|date|address",
                 "text": "точная подстрока из обращения", "start": 0, "end": 0}}],
  "signals": [{{"code": "named_official", "text": "назван конкретный служащий"}}],
  "specificity": число 0..1 — насколько обращение конкретно (ФИО, суммы, даты, организации),
  "route_to": "{CORRUPTION_ROUTE}" для коррупционных, иначе "{GENERAL_ROUTE}",
  "summary": "одно-два предложения по-русски"
}}
Не выдумывай факты, которых нет в тексте. Жалобы на ЖКХ, дороги и т.п. без признаков
коррупции — is_corruption=false, category="other"."""


class LLMAppealAnalyzer:
    """Реализует порт AppealAnalyzer через LLM."""

    def __init__(self, llm: LLMClientInterface, model_name: str) -> None:
        self._llm = llm
        self._model_name = model_name

    async def analyze(self, text: str) -> AppealAnalysis:
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=f"Обращение:\n{text}"),
        ]
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            raw = await self._llm.complete(messages, json_mode=True, temperature=0.0)
            try:
                schema = AnalysisSchema.model_validate_json(_strip_fences(raw))
            except (ValidationError, ValueError) as exc:
                last_error = exc
                logger.warning("LLM returned invalid analysis JSON (attempt {})", attempt)
                continue
            schema.analyzer = f"llm:{self._model_name}"
            return schema.to_domain(text)
        raise ExternalServiceError(f"LLM analysis is invalid: {type(last_error).__name__}")


def _strip_fences(raw: str) -> str:
    """Модели любят оборачивать JSON в ```json ... ```."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return text.strip()
