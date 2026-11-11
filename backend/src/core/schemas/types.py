from typing import Annotated

import nh3
from pydantic import AfterValidator


def _sanitize_html(value: str) -> str:
    return nh3.clean(value)


# Строка, которую ввёл человек (текст обращения, комментарий). Очищается от HTML на входе.
SafeString = Annotated[str, AfterValidator(_sanitize_html)]
