import argparse
import asyncio
import sys
from pathlib import Path

from src.core.config import BASE_DIR, get_settings_from_env
from src.core.infrastructure.database.database import get_async_session_maker, get_engine
from src.core.infrastructure.llm import OpenAICompatibleLLMClient
from src.core.infrastructure.logger import configure_logging, get_logger
from src.modules.appeals.presentation.dependencies import build_appeal_analyzer
from src.modules.appeals.presentation.seed import seed_appeals
from src.modules.counterparties.presentation.seed import seed_counterparties
from src.modules.officials.presentation.seed import seed_officials
from src.web import wiring

logger = get_logger("seed")


def _parse_args() -> argparse.Namespace:
    settings = get_settings_from_env()
    parser = argparse.ArgumentParser(prog="python -m src.seed", description=__doc__)
    parser.add_argument(
        "--dir",
        default=settings.seed_dir,
        help="каталог с JSON (по умолчанию SEED_DIR или data/generated; пример — data/example)",
    )
    parser.add_argument(
        "--no-analyze", action="store_true", help="не анализировать обращения без analysis"
    )
    parser.add_argument("--no-recompute", action="store_true", help="не пересчитывать риск")
    return parser.parse_args()


async def run(data_dir: Path, analyze: bool, recompute: bool) -> None:
    settings = get_settings_from_env()
    engine = get_engine(settings.database_url)
    session_maker = get_async_session_maker(engine)
    llm = (
        OpenAICompatibleLLMClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value() if settings.llm_api_key else None,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        )
        if settings.llm_base_url
        else None
    )
    try:
        async with session_maker() as session:
            logger.info("Seed from {}", data_dir)
            logger.info("officials: {}", await seed_officials(session, data_dir))
            logger.info("counterparties: {}", await seed_counterparties(session, data_dir))
            appeals = await seed_appeals(
                session,
                data_dir,
                analyzer=build_appeal_analyzer(settings, llm),
                directory=wiring.appeals_person_directory(session),
                analyze=analyze,
            )
            logger.info("appeals: {}", appeals)
            if recompute:
                result = await wiring.recompute_risk_use_case(session).execute()
                logger.info(
                    "risk: {} officials, {} flags {}",
                    result.officials_processed,
                    result.flags_total,
                    result.flags_by_rule,
                )
    finally:
        await engine.dispose()


def main() -> None:
    configure_logging(get_settings_from_env().log_level)
    args = _parse_args()
    data_dir = Path(args.dir)
    if not data_dir.is_absolute():
        data_dir = BASE_DIR / data_dir
    if not data_dir.is_dir():
        logger.error("Seed dir {} not found. Try: python -m src.seed --dir data/example", data_dir)
        sys.exit(1)
    asyncio.run(run(data_dir, analyze=not args.no_analyze, recompute=not args.no_recompute))


if __name__ == "__main__":
    main()
