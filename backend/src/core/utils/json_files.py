import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.core.infrastructure.logger import get_logger

logger = get_logger(__name__)


def read_json_list(path: Path) -> list[dict[str, Any]]:
    """Прочитать JSON-массив объектов. Нет файла — пустой список (сущность не загружается)."""
    if not path.exists():
        logger.info("Seed file {} not found, skipped", path.name)
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def read_models[T: BaseModel](model: type[T], path: Path) -> list[T]:
    """Прочитать и провалидировать JSON-массив объектов схемой Pydantic."""
    return [model.model_validate(row) for row in read_json_list(path)]
