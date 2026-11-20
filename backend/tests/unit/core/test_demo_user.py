import pytest
from pydantic import SecretStr

from src.core.config import Settings
from src.core.infrastructure import create_demo_user


async def test_demo_provisioning_refuses_production_before_accessing_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        auth_cookie_secure=True,
        app_env="prod", auth_secret=SecretStr("test-only-signing-key-at-least-32-characters")
    )
    monkeypatch.setattr(create_demo_user, "get_settings_from_env", lambda: settings)
    with pytest.raises(SystemExit, match="только для тестового стенда"):
        await create_demo_user.provision()
