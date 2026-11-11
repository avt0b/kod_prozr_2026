"""Загрузка сидов в одной сессии: officials -> counterparties -> appeals (с анализом) -> риск.

Используется `python -m src.seed` и e2e-тестами.
"""

from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.infrastructure.interfaces.llm_client import LLMClientInterface
from src.core.infrastructure.logger import get_logger
from src.modules.appeals.presentation.dependencies import build_appeal_analyzer
from src.modules.appeals.presentation.seed import seed_appeals
from src.modules.counterparties.presentation.seed import seed_counterparties
from src.modules.officials.presentation.seed import seed_officials
from src.web import wiring

logger = get_logger("seed")


async def load_seed(
    session: AsyncSession,
    data_dir: Path,
    settings: Settings,
    llm: LLMClientInterface | None = None,
    *,
    analyze: bool = True,
    recompute: bool = True,
) -> dict[str, Any]:
    logger.info("Seed from {}", data_dir)
    report: dict[str, Any] = {
        "officials": await seed_officials(session, data_dir),
        "counterparties": await seed_counterparties(session, data_dir),
    }
    report["appeals"] = await seed_appeals(
        session,
        data_dir,
        analyzer=build_appeal_analyzer(settings, llm),
        directory=wiring.appeals_person_directory(session),
        analyze=analyze,
    )
    for name, counts in report.items():
        logger.info("{}: {}", name, counts)
    if recompute:
        # B-10: после сидов баллы уже посчитаны, ручной POST /risk/recompute не нужен.
        result = await wiring.recompute_risk_use_case(session).execute()
        report["risk"] = {"officials": result.officials_processed, **result.flags_by_rule}
        logger.info(
            "risk: {} officials, {} flags {}",
            result.officials_processed,
            result.flags_total,
            result.flags_by_rule,
        )
    return report
