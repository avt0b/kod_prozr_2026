from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Настройки приложения.

    Имена переменных окружения — строго из docs/contracts.md (плоские, без префикса):
    DATABASE_URL, CORS_ORIGINS, LLM_BASE_URL, LLM_API_KEY, LLM_MODEL.
    Остальные поля — внутренние для бэка, у всех есть значения по умолчанию.
    """

    app_env: Literal["dev", "test", "prod"] = "dev"
    project_name: str = "Код прозрачности — рабочее место аналитика"
    version: str = "0.1.0"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://kodprozr:kodprozr@localhost:5432/kodprozr"
    db_echo: bool = False

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    # Пустой LLM_BASE_URL => LLM выключена, работают фейковые адаптеры (правила/шаблоны).
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str = "qwen2.5:7b-instruct"
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    # Установка соединения: при недоступной LLM (в т.ч. DROP на файрволе) быстро уходим на фоллбэк.
    llm_connect_timeout_seconds: float = Field(default=5.0, gt=0)

    # Каталог с JSON синтетики для `python -m src.seed` (относительно backend/ или абсолютный).
    seed_dir: str = "data/generated"
    # Порог «закупки чуть ниже порога» для R08, ₽ (тот же --threshold у генератора, data.md §3).
    procurement_threshold: float = Field(default=600_000.0, gt=0)

    model_config = SettingsConfigDict(
        env_file=f"{BASE_DIR}/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("llm_base_url", mode="before")
    @classmethod
    def empty_url_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def llm_enabled(self) -> bool:
        return self.llm_base_url is not None


@lru_cache
def get_settings_from_env() -> Settings:
    return Settings()
