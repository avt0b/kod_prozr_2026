"""ФИО: женские формы, отчества и склонение для текстов обращений.

Склонение упрощённое, но покрывает все имена из vocab.py: этого хватает, чтобы обращения
называли служащих «Соколову Андрею Викторовичу» и «Андрея Викторовича Соколова» (ai.md §3).
"""

from dataclasses import dataclass

from data.generator.vocab import _PATRONYMIC_STEMS

_HUSHING = "гкхжшчщ"


def female_surname(male: str) -> str:
    if male.endswith(("ов", "ев", "ёв", "ин", "ын")):
        return male + "а"
    if male.endswith("ий"):
        return male[:-2] + "ая"
    return male


def patronymic(father_name: str, gender: str) -> str:
    special = {"Илья": ("Ильич", "Ильинична"), "Никита": ("Никитич", "Никитична")}
    if father_name in special:
        return special[father_name][0 if gender == "m" else 1]
    stem = _PATRONYMIC_STEMS[father_name]
    base = stem[:-2]  # Андреев -> Андре, Викторов -> Виктор
    if stem.endswith("ев") or stem.endswith("ёв"):
        return base + ("евич" if gender == "m" else "евна")
    return base + ("ович" if gender == "m" else "овна")


@dataclass(frozen=True)
class FullName:
    surname: str
    name: str
    patronymic: str
    gender: str  # m | f

    @property
    def full(self) -> str:
        return f"{self.surname} {self.name} {self.patronymic}"

    @property
    def short(self) -> str:
        return f"{self.surname} {self.name[0]}. {self.patronymic[0]}."

    def initials_first(self) -> str:
        return f"{self.name[0]}.{self.patronymic[0]}. {self.surname}"

    def surname_in(self, case: str) -> str:
        return _surname(self.surname, self.gender, case)

    def full_in(self, case: str) -> str:
        return (
            f"{_surname(self.surname, self.gender, case)} {_first(self.name, self.gender, case)} "
            f"{_patronymic(self.patronymic, self.gender, case)}"
        )

    def short_in(self, case: str) -> str:
        return f"{_surname(self.surname, self.gender, case)} {self.name[0]}. {self.patronymic[0]}."

    def name_patronymic_surname(self, case: str) -> str:
        """«Андрея Викторовича Соколова» — порядок «имя отчество фамилия»."""
        return (
            f"{_first(self.name, self.gender, case)} "
            f"{_patronymic(self.patronymic, self.gender, case)} "
            f"{_surname(self.surname, self.gender, case)}"
        )


def _surname(value: str, gender: str, case: str) -> str:
    if case == "nom":
        return value
    if gender == "m":
        if value.endswith(("ов", "ев", "ёв", "ин", "ын")):
            return value + {"gen": "а", "dat": "у", "ins": "ым"}[case]
        if value.endswith("ий"):
            return value[:-2] + {"gen": "ого", "dat": "ому", "ins": "им"}[case]
        return value
    if value.endswith(("ова", "ева", "ёва", "ина", "ына")):
        return value[:-1] + {"gen": "ой", "dat": "ой", "ins": "ой"}[case]
    if value.endswith("ая"):
        return value[:-2] + {"gen": "ой", "dat": "ой", "ins": "ой"}[case]
    return value


def _first(value: str, gender: str, case: str) -> str:
    if case == "nom":
        return value
    if value.endswith("ия"):
        return value[:-1] + {"gen": "и", "dat": "и", "ins": "ей"}[case]
    if value.endswith("а"):
        soft = value[-2] in _HUSHING
        return value[:-1] + {"gen": "и" if soft else "ы", "dat": "е", "ins": "ой"}[case]
    if value.endswith("я"):
        return value[:-1] + {"gen": "и", "dat": "е", "ins": "ей"}[case]
    if value == "Любовь":
        return {"gen": "Любови", "dat": "Любови", "ins": "Любовью"}[case]
    if gender == "f":
        return value
    if value.endswith("ий"):
        return value[:-1] + {"gen": "я", "dat": "ю", "ins": "ем"}[case]
    if value.endswith(("й", "ь")):
        return value[:-1] + {"gen": "я", "dat": "ю", "ins": "ем"}[case]
    return value + {"gen": "а", "dat": "у", "ins": "ом"}[case]


def _patronymic(value: str, gender: str, case: str) -> str:
    if case == "nom":
        return value
    if gender == "m":
        return value + {"gen": "а", "dat": "у", "ins": "ем"}[case]
    return value[:-1] + {"gen": "ы", "dat": "е", "ins": "ой"}[case]
