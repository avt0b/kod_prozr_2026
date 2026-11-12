from uuid import UUID

from src.core.infrastructure.logger import get_logger
from src.modules.appeals.application.interfaces.appeal_analyzer import AppealAnalyzer
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.domain.analysis import AppealAnalysis
from src.modules.appeals.domain.appeal import Appeal
from src.modules.appeals.domain.name_matching import matches, parse_mention

logger = get_logger(__name__)


class AppealAnalysisService:
    """Сценарий «проанализировать и привязать служащих», общий для создания,
    повторного анализа и сидов. Не трогает БД и транзакции — это делают use cases.
    """

    def __init__(self, analyzer: AppealAnalyzer, directory: PersonDirectoryInterface) -> None:
        self._analyzer = analyzer
        self._directory = directory

    async def analyze(self, appeal: Appeal) -> None:
        analysis = await self._analyzer.analyze(appeal.text)
        linked = await self.link_persons(analysis)
        appeal.apply_analysis(analysis, linked)
        logger.info(
            "Appeal {} analyzed by {}: corruption={}, linked={}",
            appeal.id,
            analysis.analyzer,
            analysis.is_corruption,
            len(linked),
        )

    async def link_persons(self, analysis: AppealAnalysis) -> tuple[UUID, ...]:
        linked: list[UUID] = []
        for mention in analysis.person_mentions():
            query = parse_mention(mention)
            if query is None:
                continue
            candidates = await self._directory.find_candidates(query.surname_stem)
            found = [c.id for c in candidates if matches(c.full_name, query)]
            if len(found) == 1:
                linked.extend(found)
        return tuple(dict.fromkeys(linked))
