"""Provision a user interactively: python -m src.core.infrastructure.create_user USERNAME."""

import argparse
import asyncio
import getpass
import os
import re

from sqlalchemy import select

from src.core.config import get_settings_from_env
from src.core.infrastructure.auth import password_hasher
from src.core.infrastructure.database.database import get_async_session_maker, get_engine
from src.core.infrastructure.database.models.auth import UserModel


async def create_user(username: str, password: str) -> None:
    if not re.fullmatch(r"[a-z0-9_.-]{1,64}", username) or not 12 <= len(password) <= 256:
        raise ValueError("Логин: a-z, цифры, _.-; пароль: от 12 до 256 символов.")
    engine = get_engine(get_settings_from_env().database_url)
    try:
        async with get_async_session_maker(engine)() as db:
            if (
                await db.execute(select(UserModel.id).where(UserModel.username == username))
            ).first():
                raise ValueError("Такой пользователь уже существует.")
            db.add(
                UserModel(
                    username=username, password_hash=password_hasher.hash(password), active=True
                )
            )
            await db.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument(
        "--password-env", help="Read password from a named environment variable for automation"
    )
    args = parser.parse_args()
    password = (
        os.environ.get(args.password_env, "")
        if args.password_env
        else getpass.getpass("Пароль (не менее 12 символов): ")
    )
    if not args.password_env and password != getpass.getpass("Повторите пароль: "):
        raise SystemExit("Пароли не совпадают.")
    asyncio.run(create_user(args.username.lower(), password))
    print("Пользователь создан.")
