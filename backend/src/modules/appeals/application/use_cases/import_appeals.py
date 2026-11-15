from collections.abc import Sequence

from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.core.infrastructure.logger import get_logger
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)
from src.modules.appeals.application.services.appeal_analysis import AppealAnalysisService
from src.modules.appeals.domain.appeal import Appeal

logger = get_logger(__name__)

ANALYZE_BATCH = 20


class ImportAppealsUseCase:
    """Seed: загрузить обращения (upsert по id) и предрасчитать анализ тех, у кого его нет
    (ADR-05: фоновые обращения анализируем заранее, вживую — только демо-обращение).

    Пересчёт риска после импорта делает сам seed (полный /risk/recompute), события не нужны.
    """

    def __init__(
        self,
        repository: AppealRepositoryInterface,
        analysis: AppealAnalysisService,
        unit_of_work: UnitOfWorkInterface,
    ) -> None:
        self._repository = repository
        self._analysis = analysis
        self._unit_of_work = unit_of_work

    async def execute(self, appeals: Sequence[Appeal], analyze: bool = True) -> dict[str, int]:
        async with self._unit_of_work:
            await self._repository.upsert_many(appeals)
            await self._unit_of_work.commit()

        analyzed = 0
        while analyze:
            batch = await self._repository.list_unanalyzed(ANALYZE_BATCH)
            if not batch:
                break
            # По одному и по порядку received_at: repeated_subject ищет более ранние
            # обращения в БД, поэтому каждое сохраняется до разбора следующего.
            for appeal in batch:
                await self._analysis.analyze(appeal)
                appeal.clear_events()
                async with self._unit_of_work:
                    await self._repository.save(appeal)
                    await self._unit_of_work.commit()
            analyzed += len(batch)
            logger.info("Seed: analyzed {} appeals", analyzed)

        # appeals_precomputed — анализ пришёл из сидов (AI-06), appeals_analyzed — разобраны
        # сейчас. С предрасчётом второе 0: это норма, а не потерянный анализ.
        precomputed = sum(1 for a in appeals if a.analysis is not None)
        return {
            "appeals": len(appeals),
            "appeals_precomputed": precomputed,
            "appeals_analyzed": analyzed,
        }
