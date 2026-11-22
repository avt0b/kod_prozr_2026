"""Provision the deliberately public accounts for a test stand only: one per role (#70)."""

import asyncio

from sqlalchemy import select

from src.core.config import get_settings_from_env
from src.core.infrastructure.auth import password_hasher
from src.core.infrastructure.create_user import create_user
from src.core.infrastructure.database.database import get_async_session_maker, get_engine
from src.core.infrastructure.database.models.auth import Role, UserModel

# Public test credentials, shared with the frontend demoAccount.ts.
PASSWORD = "Demo-2026-Access!"
ACCOUNTS = {"demo": Role.ANALYST, "demo-citizen": Role.CITIZEN, "demo-admin": Role.ADMIN}
USERNAME = "demo"


async def provision() -> None:
    settings = get_settings_from_env()
    if settings.app_env == "prod":
        raise SystemExit("Демо-учётные записи предназначены только для тестового стенда.")
    missing: list[tuple[str, Role]] = []
    engine = get_engine(settings.database_url)
    try:
        async with get_async_session_maker(engine)() as db:
            for username, role in ACCOUNTS.items():
                user = (
                    await db.execute(select(UserModel).where(UserModel.username == username))
                ).scalar_one_or_none()
                if user is None:
                    missing.append((username, role))
                elif (
                    not user.active
                    or user.role != role
                    or not password_hasher.verify(PASSWORD, user.password_hash)
                ):
                    raise SystemExit(
                        f"Логин {username} занят другой учётной записью; её данные не изменены."
                    )
    finally:
        await engine.dispose()
    for username, role in missing:
        await create_user(username, PASSWORD, role)
    print(f"Демо-учётные записи готовы: {', '.join(ACCOUNTS)} / {PASSWORD}")


if __name__ == "__main__":
    asyncio.run(provision())
