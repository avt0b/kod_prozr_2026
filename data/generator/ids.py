"""Стабильные идентификаторы и реквизиты с корректными контрольными суммами."""

import random
import re
import uuid

# Пространство имён генератора: id демо-кейсов одинаковы при каждой генерации (data.md §3).
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "kodprozr:synthetic")


def stable_id(entity: str, key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{entity}:{key}"))


_INN10 = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


def _check(digits: list[int], weights: tuple[int, ...]) -> int:
    return sum(d * w for d, w in zip(digits, weights, strict=False)) % 11 % 10


def inn_legal(rng: random.Random, region: str = "77") -> str:
    """ИНН юрлица (10 цифр)."""
    digits = [int(c) for c in region] + [rng.randint(0, 9) for _ in range(7)]
    digits.append(_check(digits, _INN10))
    return "".join(map(str, digits))


def inn_person(rng: random.Random, region: str = "77") -> str:
    """ИНН физлица (12 цифр)."""
    digits = [int(c) for c in region] + [rng.randint(0, 9) for _ in range(8)]
    digits.append(_check(digits, _INN11))
    digits.append(_check(digits, _INN12))
    return "".join(map(str, digits))


def ogrn(rng: random.Random, year: int, region: str = "77") -> str:
    """ОГРН (13 цифр): признак 1, год регистрации, регион, номер, контрольная цифра."""
    body = f"1{year % 100:02d}{region}{rng.randint(0, 9_999_999):07d}"[:12]
    body = body.ljust(12, "0")
    return body + str(int(body) % 11 % 10)


def is_valid_inn(value: str) -> bool:
    if not value.isdigit():
        return False
    digits = [int(c) for c in value]
    if len(digits) == 10:
        return digits[9] == _check(digits[:9], _INN10)
    if len(digits) == 12:
        return digits[10] == _check(digits[:10], _INN11) and digits[11] == _check(
            digits[:11], _INN12
        )
    return False


def is_valid_ogrn(value: str) -> bool:
    return len(value) == 13 and value.isdigit() and int(value[:12]) % 11 % 10 == int(value[12])


# --- Нормализация контактов: та же логика, что в backend/src/modules/risk/domain/contacts.py.
_NOT_WORD = re.compile(r"[^\w]+")
_ADDRESS_STOPWORDS = frozenset(
    {
        "г", "гор", "город", "обл", "область", "р", "н", "р-н", "район", "пос", "поселок",
        "с", "село", "ул", "улица", "пр", "пр-т", "просп", "проспект", "пер", "переулок",
        "ш", "шоссе", "наб", "набережная", "б-р", "бульвар", "пл", "площадь", "мкр",
        "д", "дом", "к", "корп", "корпус", "стр", "строение", "лит", "литера",
    }
)  # fmt: skip
_UNIT_WORDS = frozenset({"кв", "квартира", "оф", "офис", "пом", "помещение", "комн", "комната"})


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else None


def normalize_address(address: str | None) -> str | None:
    if not address:
        return None
    tokens = _NOT_WORD.sub(" ", address.lower().replace("ё", "е")).split()
    result = ["#" if t in _UNIT_WORDS else t for t in tokens if t not in _ADDRESS_STOPWORDS]
    return " ".join(result) or None
