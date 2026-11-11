from src.core.exceptions import DomainValidationError, ExternalServiceError
from src.core.infrastructure.logger import get_logger
from src.modules.appeals.application.interfaces.appeal_analyzer import AppealAnalyzer
from src.modules.appeals.domain.analysis import AppealAnalysis

logger = get_logger(__name__)


class FallbackAppealAnalyzer:
    """«Сначала LLM, при сбое — правила» (ADR-05). Демо не падает, если LLM недоступна."""

    def __init__(self, primary: AppealAnalyzer, fallback: AppealAnalyzer) -> None:
        self._primary = primary
        self._fallback = fallback

    async def analyze(self, text: str) -> AppealAnalysis:
        try:
            return await self._primary.analyze(text)
        except (ExternalServiceError, DomainValidationError) as exc:
            logger.warning("Primary appeal analyzer failed ({}), using fallback", exc.message)
            return await self._fallback.analyze(text)
