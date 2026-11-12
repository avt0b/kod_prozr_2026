"""Анализ обращения через LLM (OpenAI-совместимый API) по порту LLMClientInterface из core.

Промпт — черновик: финальную версию с few-shot ведёт Влад О. (docs/ai.md). Ответ всегда
валидируется схемой; при невалидном JSON — один повтор, затем ExternalServiceError
(его перехватывает FallbackAppealAnalyzer и уходит в правила).
"""

from src.core.infrastructure.interfaces.llm_client import ChatMessage, LLMClientInterface
from src.core.infrastructure.llm.structured import complete_model
from src.modules.appeals.domain.analysis import CORRUPTION_ROUTE, GENERAL_ROUTE, AppealAnalysis
from src.modules.appeals.infrastructure.serialization import AnalysisSchema

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
        schema = await complete_model(
            self._llm, SYSTEM_PROMPT, [ChatMessage("user", f"Обращение:\n{text}")], AnalysisSchema
        )
        schema.analyzer = f"llm:{self._model_name}"
        return schema.to_domain(text)
