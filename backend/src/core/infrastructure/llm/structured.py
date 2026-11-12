from pydantic import BaseModel, ValidationError

from src.core.exceptions.base import LLMInvalidResponseError
from src.core.infrastructure.interfaces.llm_client import ChatMessage, LLMClientInterface
from src.core.infrastructure.logger import get_logger

logger = get_logger(__name__)


async def complete_model[T: BaseModel](
    client: LLMClientInterface, system: str, messages: list[ChatMessage], model: type[T]
) -> T:
    for attempt in range(2):
        try:
            data = await client.complete_json(system, messages, model.model_json_schema())
            return model.model_validate(data)
        except (LLMInvalidResponseError, ValidationError):
            logger.warning("Invalid structured LLM response: attempt={}", attempt + 1)
            # No echoed values: validation errors may contain citizen text.
            messages = [
                *messages,
                ChatMessage("user", "Ответ не соответствует JSON-схеме. Исправь его."),
            ]
    raise LLMInvalidResponseError("LLM response failed schema validation after retry")
