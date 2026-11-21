"""Provision the deliberately public account for a test stand only."""

import asyncio

from sqlalchemy import select

from src.core.config import get_settings_from_env
from src.core.infrastructure.auth import password_hasher
from src.core.infrastructure.create_user import create_user
from src.core.infrastructure.database.database import get_async_session_maker, get_engine
from src.core.infrastructure.database.models.auth import UserModel

USERNAME = "demo"
PASSWORD = "Demo-2026-Access!"  # Public test credentials, shared with the frontend demoAccount.ts.


async def provision() -> None:
    settings = get_settings_from_env()
    if settings.app_env == "prod":
        raise SystemExit("Демо-учётная запись предназначена только для тестового стенда.")
    engine = get_engine(settings.database_url)
    try:
        async with get_async_session_maker(engine)() as db:
            user = (
                await db.execute(select(UserModel).where(UserModel.username == USERNAME))
            ).scalar_one_or_none()
            if user is not None:
                if not user.active or not password_hasher.verify(PASSWORD, user.password_hash):
                    raise SystemExit(
                        "Логин demo занят другой учётной записью; её данные не изменены."
                    )
                print("Демо-учётная запись уже готова.")
                return
    finally:
        await engine.dispose()
    await create_user(USERNAME, PASSWORD)
    print("Демо-учётная запись создана.")


if __name__ == "__main__":
    asyncio.run(provision())
