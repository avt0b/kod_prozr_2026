"""AI-06: предрасчёт анализа обращений в сиды, чтобы стенд не зависел от скорости LLM.

    python -m src.seed.precompute --dir ../data/generated --keep-new <appeal_id> [...]

Загружает сиды, заново разбирает все обращения (LLM, если задан LLM_BASE_URL, иначе
фоллбэк), сопоставляет лица и записывает `analysis`, `linked_person_ids` и статус обратно
в appeals.json. Обращения из --keep-new остаются `new`: их разбирают вживую на демо.
После этого `python -m src.seed` загружает предрасчёт и анализ не повторяет.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from src.core.config import BASE_DIR, get_settings_from_env
from src.core.infrastructure.database.database import get_async_session_maker, get_engine
from src.core.infrastructure.llm import OpenAICompatibleLLMClient
from src.core.infrastructure.logger import configure_logging, get_logger
from src.modules.appeals.infrastructure.repositories.appeal_repository import AppealRepository
from src.modules.appeals.infrastructure.serialization import analysis_to_json
from src.seed.loader import load_seed

logger = get_logger("seed.precompute")


async def precompute(data_dir: Path, keep_new: set[str]) -> dict[str, int]:
    settings = get_settings_from_env()
    engine = get_engine(settings.database_url)
    llm = (
        OpenAICompatibleLLMClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value() if settings.llm_api_key else None,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
            connect_timeout=settings.llm_connect_timeout_seconds,
        )
        if settings.llm_base_url
        else None
    )
    path = data_dir / "appeals.json"
    rows: list[dict[str, Any]] = json.loads(path.read_text("utf-8"))
    engines: dict[str, int] = {}
    try:
        async with get_async_session_maker(engine)() as session:
            await load_seed(session, data_dir, settings, llm, recompute=False, reanalyze=True)
            repository = AppealRepository(session)
            for row in rows:
                if row["id"] in keep_new:
                    row.update(status="new", analysis=None, linked_person_ids=[])
                    continue
                appeal = await repository.get(UUID(row["id"]))
                if appeal is None or appeal.analysis is None:
                    raise RuntimeError(f"appeal {row['id']} was not analyzed")
                row.update(
                    status="analyzed",
                    analysis=analysis_to_json(appeal.analysis),
                    linked_person_ids=[str(p) for p in appeal.linked_person_ids],
                )
                engines[appeal.analysis.engine] = engines.get(appeal.analysis.engine, 0) + 1
    finally:
        if llm is not None:
            await llm.aclose()
        await engine.dispose()
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"appeals": len(rows), "kept_new": len(keep_new), **engines}


def main() -> None:
    settings = get_settings_from_env()
    configure_logging(settings.log_level)
    parser = argparse.ArgumentParser(prog="python -m src.seed.precompute", description=__doc__)
    parser.add_argument("--dir", default=settings.seed_dir)
    parser.add_argument("--keep-new", nargs="*", default=[], help="id обращений для живого демо")
    args = parser.parse_args()
    data_dir = Path(args.dir)
    if not data_dir.is_absolute():
        data_dir = BASE_DIR / data_dir
    if not (data_dir / "appeals.json").is_file():
        logger.error("{} has no appeals.json", data_dir)
        sys.exit(1)
    result = asyncio.run(precompute(data_dir, set(args.keep_new)))
    logger.info("Precomputed: {}", result)


if __name__ == "__main__":
    main()
