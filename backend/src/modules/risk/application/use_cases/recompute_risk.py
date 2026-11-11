from collections import Counter
from collections.abc import Sequence
from uuid import UUID

from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.core.infrastructure.logger import get_logger
from src.modules.risk.application.dto.risk_dto import RecomputeResultDTO
from src.modules.risk.application.interfaces.risk_repository import RiskRepositoryInterface
from src.modules.risk.application.services.world_loader import RiskWorldLoader
from src.modules.risk.domain.engine import RiskEngine

logger = get_logger(__name__)


class RecomputeRiskUseCase:
    """POST /risk/recompute: пересчитать все флаги и баллы.

    С person_ids — частичный пересчёт только этих людей (ADR-10: после анализа обращения
    пересчитываются привязанные к нему служащие). Правила R01–R07 смотрят только на своего
    служащего, поэтому частичный пересчёт даёт тот же результат, что и полный.
    TODO(R08): сравнение с коллегами зависит от всей группы — для него нужен полный пересчёт.

    Считаем синхронно: на объёме синтетики (тысячи служащих) это секунды.
    Если станет долго — вынести в фон (asyncio task / очередь) и отдавать 202.
    """

    def __init__(
        self,
        loader: RiskWorldLoader,
        engine: RiskEngine,
        repository: RiskRepositoryInterface,
        unit_of_work: UnitOfWorkInterface,
    ) -> None:
        self._loader = loader
        self._engine = engine
        self._repository = repository
        self._unit_of_work = unit_of_work

    async def execute(self, person_ids: Sequence[UUID] | None = None) -> RecomputeResultDTO:
        world = await self._loader.load(person_ids)
        assessment = self._engine.assess(world)

        async with self._unit_of_work:
            if person_ids is None:
                await self._repository.replace_all(assessment.flags, assessment.scores)
            else:
                await self._repository.replace_for_persons(
                    list(person_ids), assessment.flags, assessment.scores
                )
            await self._unit_of_work.commit()

        by_rule = Counter(flag.rule_code.value for flag in assessment.flags)
        logger.info(
            "Risk recomputed: {} officials, {} flags", len(assessment.scores), len(assessment.flags)
        )
        return RecomputeResultDTO(
            officials_processed=len(assessment.scores),
            flags_total=len(assessment.flags),
            flags_by_rule=dict(sorted(by_rule.items())),
            computed_at=assessment.computed_at,
        )
