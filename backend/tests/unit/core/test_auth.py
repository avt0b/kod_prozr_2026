from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from src.core.config import Settings
from src.core.infrastructure.auth import decode_access, password_hasher

KEY = "test-only-jwt-secret-of-at-least-thirty-two-characters"


@pytest.mark.parametrize(
    "patch",
    [
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        {"aud": "another-service"},
        {"iss": "another-issuer"},
        {"type": "refresh"},
        {"sub": "not-a-uuid"},
    ],
)
def test_invalid_claims(patch: dict[str, object]) -> None:
    now = datetime.now(UTC)
    claims = {
        "sub": str(uuid4()),
        "sid": str(uuid4()),
        "iss": "kod-prozr",
        "aud": "kod-prozr-api",
        "type": "access",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
        **patch,
    }
    with pytest.raises(HTTPException) as error:
        decode_access(
            jwt.encode(claims, KEY, algorithm="HS256"), Settings(auth_secret=SecretStr(KEY))
        )
    assert error.value.status_code == 401


def test_password_is_argon2_and_salted() -> None:
    first = password_hasher.hash("a-password-of-at-least-12")
    second = password_hasher.hash("a-password-of-at-least-12")
    assert first.startswith("$argon2id$") and first != second
    assert password_hasher.verify("a-password-of-at-least-12", first)
    assert not password_hasher.verify("wrong", first)


def test_required_claims_and_algorithm() -> None:
    for claims, algorithm in [({"sub": str(uuid4())}, "HS256"), ({"sub": str(uuid4())}, "HS384")]:
        with pytest.raises(HTTPException) as error:
            decode_access(
                jwt.encode(claims, KEY, algorithm=algorithm), Settings(auth_secret=SecretStr(KEY))
            )
        assert error.value.status_code == 401
