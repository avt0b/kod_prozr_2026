from dataclasses import replace

from src.core.infrastructure.logger import get_logger
from src.modules.appeals.application.interfaces.appeal_analyzer import AppealAnalyzer
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.application.interfaces.person_matcher import (
    MatchResult,
    OfficialCard,
    PersonMatcherInterface,
)
from src.modules.appeals.domain.analysis import AppealAnalysis
from src.modules.appeals.domain.appeal import Appeal

logger = get_logger(__name__)


class AppealAnalysisService:
    """Сценарий «проанализировать и привязать служащих», общий для создания,
    повторного анализа и сидов. Не трогает БД и транзакции — это делают use cases.

    Справочник служащих загружается один раз на экземпляр сервиса: сиды анализируют
    сотню обращений подряд, а HTTP-запрос создаёт сервис заново.
    """

    def __init__(
        self,
        analyzer: AppealAnalyzer,
        directory: PersonDirectoryInterface,
        matcher: PersonMatcherInterface,
    ) -> None:
        self._analyzer = analyzer
        self._directory = directory
        self._matcher = matcher
        self._officials: list[OfficialCard] | None = None

    async def analyze(self, appeal: Appeal) -> None:
        analysis = await self._analyzer.analyze(appeal.text)
        match = await self.match(analysis, appeal)
        appeal.apply_analysis(replace(analysis, candidates=match.candidates), match.linked)
        logger.info(
            "Appeal {} analyzed by {}: corruption={}, linked={}, candidates={}",
            appeal.id,
            analysis.analyzer,
            analysis.is_corruption,
            len(match.linked),
            len(match.candidates),
        )

    async def match(self, analysis: AppealAnalysis, appeal: Appeal) -> MatchResult:
        if self._officials is None:
            self._officials = await self._directory.officials()
        return self._matcher.match(
            analysis, appeal.text, self._officials, appeal.received_at.date()
        )
