import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from src.core.infrastructure.logger import get_logger

logger = get_logger(__name__)


def read_json_list(path: Path) -> list[dict[str, Any]]:
    """Прочитать JSON-массив объектов. Нет файла — пустой список (сущность не загружается)."""
    if not path.exists():
        logger.info("Seed file {} not found, skipped", path.name)
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise ValueError(f"{path}: cannot read JSON ({type(exc).__name__})") from exc
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    for index, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: record {index} must be an object")
    return data


def read_models[T: BaseModel](model: type[T], path: Path) -> list[T]:
    """Прочитать и провалидировать JSON-массив объектов схемой Pydantic."""
    result = []
    for index, row in enumerate(read_json_list(path), start=1):
        try:
            result.append(model.model_validate(row))
        except ValidationError as exc:
            fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
            raise ValueError(f"{path}: record {index}: invalid fields: {fields}") from exc
    return result
