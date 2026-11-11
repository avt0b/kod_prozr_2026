"""Нормализация адресов и телефонов для сравнения (R05)."""

import re

_PHONE_DIGITS = 10
_NOT_WORD = re.compile(r"[^\w]+")
# Служебные слова адреса: «г. Энск, ул. Ленина, д. 5» == «Энск Ленина 5».
_ADDRESS_STOPWORDS = frozenset(
    {
        "г", "гор", "город", "обл", "область", "р", "н", "р-н", "район", "пос", "поселок",
        "с", "село", "ул", "улица", "пр", "пр-т", "просп", "проспект", "пер", "переулок",
        "ш", "шоссе", "наб", "набережная", "б-р", "бульвар", "пл", "площадь", "мкр",
        "д", "дом", "к", "корп", "корпус", "стр", "строение", "лит", "литера",
    }
)  # fmt: skip
# Квартира и офис — одна и та же «единица помещения»: «кв. 12» и «оф. 12» совпадают.
_UNIT_WORDS = frozenset({"кв", "квартира", "оф", "офис", "пом", "помещение", "комн", "комната"})


def normalize_phone(phone: str | None) -> str | None:
    """Последние 10 цифр: «+7 (900) 000-00-01» и «8 900 0000001» совпадают."""
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits[-_PHONE_DIGITS:] if len(digits) >= _PHONE_DIGITS else None


def normalize_address(address: str | None) -> str | None:
    if not address:
        return None
    tokens = _NOT_WORD.sub(" ", address.lower().replace("ё", "е")).split()
    result: list[str] = []
    for token in tokens:
        if token in _ADDRESS_STOPWORDS:
            continue
        result.append("#" if token in _UNIT_WORDS else token)
    return " ".join(result) or None
