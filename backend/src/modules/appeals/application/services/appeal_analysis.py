from dataclasses import replace
from uuid import UUID

from src.core.infrastructure.logger import get_logger
from src.modules.appeals.application.interfaces.appeal_analyzer import AppealAnalyzer
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.application.interfaces.person_matcher import (
    MatchResult,
    OfficialCard,
    PersonMatcherInterface,
)
from src.modules.appeals.domain.analysis import AppealAnalysis
from src.modules.appeals.domain.appeal import Appeal
from src.modules.appeals.domain.repeats import (
    REPEAT_WINDOW,
    RepeatedSubject,
    company_keys,
    find_repeats,
    with_repeated_subject,
)

logger = get_logger(__name__)


class AppealAnalysisService:
    """Сценарий «проанализировать, привязать служащих и найти повторы», общий для создания,
    повторного анализа и сидов. Читает другие обращения (repeated_subject), но не пишет в БД
    и не управляет транзакциями — это делают use cases.

    Справочник служащих загружается один раз на экземпляр сервиса: сиды анализируют
    сотню обращений подряд, а HTTP-запрос создаёт сервис заново.
    """

    def __init__(
        self,
        analyzer: AppealAnalyzer,
        directory: PersonDirectoryInterface,
        matcher: PersonMatcherInterface,
        repository: AppealRepositoryInterface,
    ) -> None:
        self._analyzer = analyzer
        self._directory = directory
        self._matcher = matcher
        self._repository = repository
        self._officials: list[OfficialCard] | None = None

    async def analyze(self, appeal: Appeal) -> None:
        analysis = await self._analyzer.analyze(appeal.text)
        match = await self.match(analysis, appeal)
        repeat = await self.repeats(analysis, appeal, match.linked)
        analysis = with_repeated_subject(replace(analysis, candidates=match.candidates), repeat)
        appeal.apply_analysis(analysis, match.linked)
        logger.info(
            "Appeal {} analyzed by {}: corruption={}, linked={}, candidates={}, repeats={}",
            appeal.id,
            analysis.analyzer,
            analysis.is_corruption,
            len(match.linked),
            len(match.candidates),
            len(repeat.appeal_ids) if repeat else 0,
        )

    async def match(self, analysis: AppealAnalysis, appeal: Appeal) -> MatchResult:
        if self._officials is None:
            self._officials = await self._directory.officials()
        return self._matcher.match(
            analysis, appeal.text, self._officials, appeal.received_at.date()
        )

    async def repeats(
        self, analysis: AppealAnalysis, appeal: Appeal, linked: tuple[UUID, ...]
    ) -> RepeatedSubject | None:
        """repeated_subject (ai.md §2): тот же служащий или компания в более ранних обращениях
        за REPEAT_WINDOW. Считает код и для LLM, и для фоллбэка."""
        companies = company_keys(analysis)
        if not linked and not companies:
            return None
        others = await self._repository.prior_subjects(
            exclude_id=appeal.id,
            since=appeal.received_at - REPEAT_WINDOW,
            before=appeal.received_at,
            person_ids=linked,
            with_companies=bool(companies),
        )
        return find_repeats(appeal.id, appeal.received_at, linked, companies, others)
