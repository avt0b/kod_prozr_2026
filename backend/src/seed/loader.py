"""Загрузка сидов в одной сессии: officials -> counterparties -> appeals (с анализом) -> риск.

Используется `python -m src.seed` и e2e-тестами.
"""

from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.infrastructure.interfaces.llm_client import LLMClientInterface
from src.core.infrastructure.logger import get_logger
from src.modules.appeals.presentation.dependencies import build_appeal_analyzer
from src.modules.appeals.presentation.seed import seed_appeals
from src.modules.counterparties.presentation.seed import seed_counterparties
from src.modules.officials.presentation.seed import seed_officials
from src.seed.validation import SCHEMAS, validate_snapshot
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
    reanalyze: bool = False,
) -> dict[str, Any]:
    with TemporaryDirectory(prefix="kodprozr-seed-") as temp:
        snapshot = Path(temp)
        for name in SCHEMAS:
            source = data_dir / f"{name}.json"
            if not source.is_file():
                raise ValueError(f"{source}: required seed file is missing")
            copyfile(source, snapshot / source.name)
        validate_snapshot(snapshot)
        async with session.begin():
            connection = await session.connection()
            async with AsyncSession(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            ) as importing:
                await importing.execute(
                    text(
                        "TRUNCATE TABLE core.audit_log, reports.report_drafts, "
                        "risk.flags, risk.scores, "
                        "appeals.appeals, counterparties.contracts, counterparties.company_roles, "
                        "counterparties.companies, officials.appointments, officials.authorities, "
                        "officials.positions, officials.kinships, officials.employments, "
                        "officials.persons, officials.organs"
                    )
                )
                return await _import(
                    importing, snapshot, settings, llm, analyze, recompute, reanalyze
                )


async def _import(
    session: AsyncSession,
    data_dir: Path,
    settings: Settings,
    llm: LLMClientInterface | None,
    analyze: bool,
    recompute: bool,
    reanalyze: bool = False,
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
        reanalyze=reanalyze,
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
