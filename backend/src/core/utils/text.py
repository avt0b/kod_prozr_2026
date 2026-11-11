import re

_SPACES = re.compile(r"\s+")


def normalize_spaces(value: str) -> str:
    return _SPACES.sub(" ", value).strip()


def short_name(full_name: str) -> str:
    """«Иванов Иван Иванович» -> «Иванов И.И.»."""
    parts = normalize_spaces(full_name).split(" ")
    if len(parts) < 2:
        return full_name
    initials = "".join(f"{part[0]}." for part in parts[1:3] if part)
    return f"{parts[0]} {initials}"


def format_rub(amount: float) -> str:
    """12500000 -> «12,5 млн руб.»."""
    if amount >= 1_000_000_000:
        return f"{amount / 1_000_000_000:.1f} млрд руб.".replace(".", ",", 1)
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f} млн руб.".replace(".", ",", 1)
    if amount >= 1_000:
        return f"{amount / 1_000:.0f} тыс. руб."
    return f"{amount:.0f} руб."
