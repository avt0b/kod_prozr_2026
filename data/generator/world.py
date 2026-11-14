"""Построение синтетического мира: органы, служащие, связи, компании, контракты, кейсы, шум.

Все случайности идут через один `random.Random(seed)`, а ключи id — через stable_id, поэтому
генерация воспроизводима. Кейсы описаны в docs/data.md §4–5; разметка — в `self.schemes`.
"""

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from data.generator import vocab
from data.generator.ids import (
    inn_legal,
    inn_person,
    normalize_address,
    normalize_phone,
    ogrn,
    stable_id,
)
from data.generator.names import FullName, female_surname, patronymic

Row = dict[str, Any]

CONTRACTS_FROM = date(2023, 1, 10)
CONTRACTS_TO = date(2026, 10, 31)
SNAPSHOT = date(2026, 11, 10)

MASS_ADDRESSES = ("г. Энск, ул. Промышленная, д. 12", "г. Энск, пр-т Строителей, д. 40")


@dataclass
class Official:
    person_id: str
    name: FullName
    organ: str
    position_key: str
    appointment_id: str
    started_at: date
    ended_at: date | None
    scope: tuple[str, ...]  # коды ОКПД2 полномочия procurement (пусто — нет кодов/полномочия)
    procurement: bool
    authorities: tuple[str, ...]
    address: str
    phone: str
    case: str | None = None
    relatives: list[tuple[str, str, FullName]] = field(default_factory=list)  # id, kind, name


@dataclass
class Scheme:
    case_id: str
    rule_codes: list[str]
    person_id: str
    evidence_ids: list[str]
    note: str


def _days(a: date, b: date) -> int:
    return (b - a).days


class WorldBuilder:
    def __init__(self, seed: int, threshold: float) -> None:
        self.rng = random.Random(seed)
        self.threshold = threshold
        self.rows: dict[str, list[Row]] = defaultdict(list)
        self.schemes: list[Scheme] = []
        self.peer_anomalies: list[dict[str, Any]] = []
        self.officials: dict[str, Official] = {}
        self.organ_ids: dict[str, str] = {}
        self.organ_inn: dict[str, str] = {}
        self.position_ids: dict[tuple[str, str], str] = {}
        self.slots: dict[tuple[str, str, int], Official] = {}
        self.suppliers: dict[tuple[str, str], list[str]] = {}
        self.companies: dict[str, Row] = {}
        self._phones: set[str] = set()
        self._addresses: set[str] = set()
        self._inns: set[str] = set()
        self._full_names: set[str] = set()
        self._official_surnames: set[str] = set()
        self._company_names: set[str] = set()
        self._contract_seq: dict[tuple[str, int], int] = defaultdict(int)
        self._counter: dict[str, int] = defaultdict(int)
        self._outsider_load: dict[str, int] = {}
        surnames = [
            s for s in dict.fromkeys(vocab.MALE_SURNAMES) if s not in vocab.RESERVED_SURNAMES
        ]
        self._surnames = surnames

    # ------------------------------------------------------------------ helpers
    def _key(self, prefix: str) -> str:
        self._counter[prefix] += 1
        return f"{prefix}{self._counter[prefix]}"

    def _date(self, start: date, end: date) -> date:
        return start + timedelta(days=self.rng.randint(0, max(0, _days(start, end))))

    def _phone(self, value: str | None = None) -> str:
        if value is not None:
            self._phones.add(normalize_phone(value) or value)
            return value
        while True:
            phone = (
                f"+7 9{self.rng.randint(0, 99):02d} {self.rng.randint(100, 999)}-"
                f"{self.rng.randint(10, 99)}-{self.rng.randint(10, 99)}"
            )
            norm = normalize_phone(phone)
            if norm not in self._phones:
                self._phones.add(norm or phone)
                return phone

    def _address(self, unit: str = "кв.", value: str | None = None) -> str:
        if value is not None:
            self._addresses.add(normalize_address(value) or value)
            return value
        while True:
            town = self.rng.choice(vocab.TOWNS)
            street = self.rng.choice(vocab.STREETS)
            address = (
                f"{town}, {street}, д. {self.rng.randint(1, 120)}, "
                f"{unit} {self.rng.randint(1, 240)}"
            )
            norm = normalize_address(address)
            if norm not in self._addresses:
                self._addresses.add(norm or address)
                return address

    def _inn_person(self) -> str:
        while True:
            value = inn_person(self.rng)
            if value not in self._inns:
                self._inns.add(value)
                return value

    def _inn_legal(self) -> str:
        while True:
            value = inn_legal(self.rng)
            if value not in self._inns:
                self._inns.add(value)
                return value

    def random_name(self, gender: str | None = None, surname: str | None = None) -> FullName:
        gender = gender or self.rng.choice("mf")
        for _ in range(500):
            base = surname or self.rng.choice(self._surnames)
            last = base if gender == "m" else female_surname(base)
            first = self.rng.choice(vocab.MALE_NAMES if gender == "m" else vocab.FEMALE_NAMES)
            father = self.rng.choice(vocab.MALE_NAMES)
            name = FullName(last, first, patronymic(father, gender), gender)
            if name.full not in self._full_names:
                return name
        raise RuntimeError("name space exhausted")

    def person(
        self,
        key: str,
        name: FullName,
        *,
        birth: date | None = None,
        address: str | None = None,
        phone: str | None = None,
        with_inn: bool = True,
        allow_duplicate_name: bool = False,
    ) -> str:
        if name.full in self._full_names and not allow_duplicate_name:
            raise ValueError(f"duplicate person name {name.full}")
        self._full_names.add(name.full)
        pid = stable_id("person", key)
        self.rows["persons"].append(
            {
                "id": pid,
                "full_name": name.full,
                "inn": self._inn_person() if with_inn else None,
                "birth_date": (
                    birth or self._date(date(1960, 1, 1), date(1998, 12, 31))
                ).isoformat(),
                "address": address if address is not None else self._address(),
                "phone": phone if phone is not None else self._phone(),
            }
        )
        return pid

    def person_row(self, person_id: str) -> Row:
        return next(p for p in self.rows["persons"] if p["id"] == person_id)

    # ------------------------------------------------------------------ organs & positions
    def build_organs(self) -> None:
        for code, (name, region) in vocab.ORGANS.items():
            oid = stable_id("organ", code)
            inn = self._inn_legal()
            self.organ_ids[code] = oid
            self.organ_inn[code] = inn
            self.rows["organs"].append({"id": oid, "name": name, "inn": inn, "region": region})
            for key, dept, title, auths, _holders in vocab.POSITIONS[code]:
                pid = stable_id("position", f"{code}:{key}")
                self.position_ids[(code, key)] = pid
                self.rows["positions"].append(
                    {
                        "id": pid,
                        "organ_id": oid,
                        "title": title,
                        "department": dept,
                        "is_corruption_risky": bool(auths),
                    }
                )
                for kind, okpd2 in auths:
                    self.rows["authorities"].append(
                        {
                            "id": stable_id("authority", f"{code}:{key}:{kind}"),
                            "position_id": pid,
                            "kind": kind,
                            "scope": {
                                "okpd2": list(okpd2),
                                "okved": [],
                                "territory": "г. Энск" if code == "O3" else "Энская область",
                            },
                        }
                    )

    def _position_meta(self, organ: str, key: str) -> tuple[str, str, tuple[vocab.Auth, ...]]:
        for k, dept, title, auths, _ in vocab.POSITIONS[organ]:
            if k == key:
                return dept, title, auths
        raise KeyError(key)

    def appoint(
        self,
        organ: str,
        key: str,
        name: FullName,
        *,
        person_key: str,
        started_at: date,
        ended_at: date | None = None,
        birth: date | None = None,
        case: str | None = None,
        address: str | None = None,
        phone: str | None = None,
    ) -> Official:
        if name.surname in self._official_surnames and case is None:
            raise ValueError("official surname reuse")
        self._official_surnames.add(name.surname)
        address = address or self._address()
        phone = phone or self._phone()
        pid = self.person(person_key, name, birth=birth, address=address, phone=phone)
        appointment_id = stable_id("appointment", f"{person_key}:{organ}:{key}")
        self.rows["appointments"].append(
            {
                "id": appointment_id,
                "person_id": pid,
                "position_id": self.position_ids[(organ, key)],
                "started_at": started_at.isoformat(),
                "ended_at": ended_at.isoformat() if ended_at else None,
            }
        )
        _dept, _title, auths = self._position_meta(organ, key)
        scope = tuple(code for kind, codes in auths if kind == "procurement" for code in codes)
        official = Official(
            person_id=pid,
            name=name,
            organ=organ,
            position_key=key,
            appointment_id=appointment_id,
            started_at=started_at,
            ended_at=ended_at,
            scope=scope,
            procurement=any(kind == "procurement" for kind, _ in auths),
            authorities=tuple(kind for kind, _ in auths),
            address=address,
            phone=phone,
            case=case,
        )
        self.officials[pid] = official
        return official

    def new_official_name(self, gender: str | None = None) -> FullName:
        for _ in range(500):
            name = self.random_name(gender)
            if name.surname not in self._official_surnames and (
                female_surname(name.surname) not in self._official_surnames
            ):
                base = name.surname if name.gender == "m" else name.surname[:-1]
                if (
                    base not in self._official_surnames
                    and base + "а" not in self._official_surnames
                ):
                    return name
        raise RuntimeError("official surnames exhausted")

    def relative(
        self,
        official: Official,
        kind: str,
        name: FullName | None = None,
        *,
        key: str | None = None,
        address: str | None = None,
        phone: str | None = None,
        birth: date | None = None,
    ) -> str:
        if name is None:
            name = self._relative_name(official, kind)
        key = key or self._key(f"rel:{official.person_id}:")
        rid = self.person(key, name, address=address, phone=phone, birth=birth)
        self.rows["kinships"].append(
            {
                "id": stable_id("kinship", key),
                "person_id": official.person_id,
                "relative_id": rid,
                "kind": kind,
            }
        )
        official.relatives.append((rid, kind, name))
        return rid

    def _relative_name(self, official: Official, kind: str) -> FullName:
        male_base = (
            official.name.surname if official.name.gender == "m" else official.name.surname[:-1]
        )
        gender = self.rng.choice("mf")
        if kind == "spouse":
            gender = "f" if official.name.gender == "m" else "m"
        same_family = kind in ("child", "sibling") or (
            kind in ("spouse", "parent") and self.rng.random() < 0.7
        )
        for _ in range(200):
            surname = male_base if same_family else self.rng.choice(self._surnames)
            name = self.random_name(gender, surname=surname)
            if kind in ("child", "sibling") and official.name.gender == "m":
                pass
            if name.full not in self._full_names:
                return name
        return self.random_name(gender)

    # ------------------------------------------------------------------ companies
    def company_name(self, form: str = "ООО") -> str:
        while True:
            a = self.rng.choice(vocab.COMPANY_WORDS_A)
            b = self.rng.choice(vocab.COMPANY_WORDS_B)
            if a == b:
                continue
            name = f"{form} «{a}{b.lower() if self.rng.random() < 0.6 else b}»"
            if self.rng.random() < 0.25:
                name = f"{form} «{a}{b.lower()}-{self.rng.choice(['М', 'Т', 'С', 'Э', '1', '2'])}»"
            if name not in self._company_names:
                self._company_names.add(name)
                return name

    def company(
        self,
        key: str,
        *,
        okved: str,
        name: str | None = None,
        registered_at: date | None = None,
        status: str = "active",
        address: str | None = None,
        phone: str | None = None,
    ) -> str:
        if name is not None:
            if name in self._company_names:
                raise ValueError(f"duplicate company {name}")
            self._company_names.add(name)
        else:
            name = self.company_name("АО" if self.rng.random() < 0.07 else "ООО")
        registered = registered_at or self._date(date(2004, 1, 1), date(2021, 6, 30))
        cid = stable_id("company", key)
        row = {
            "id": cid,
            "inn": self._inn_legal(),
            "ogrn": ogrn(self.rng, registered.year),
            "name": name,
            "okved": okved,
            "address": address if address is not None else self._address("оф."),
            "phone": phone if phone is not None else self._phone(),
            "registered_at": registered.isoformat(),
            "status": status,
        }
        self.rows["companies"].append(row)
        self.companies[cid] = row
        return cid

    def role(
        self,
        company_id: str,
        person_id: str,
        role: str,
        *,
        started_at: date | None = None,
        share: float | None = None,
        ended_at: date | None = None,
    ) -> str:
        company = self.companies[company_id]
        start = started_at or date.fromisoformat(company["registered_at"])
        rid = stable_id("company_role", f"{company_id}:{person_id}:{role}:{start}")
        self.rows["company_roles"].append(
            {
                "id": rid,
                "company_id": company_id,
                "person_id": person_id,
                "role": role,
                "share": share,
                "started_at": start.isoformat(),
                "ended_at": ended_at.isoformat() if ended_at else None,
            }
        )
        return rid

    def employment(
        self, person_id: str, company_id: str, started_at: date, ended_at: date | None
    ) -> str:
        eid = stable_id("employment", f"{person_id}:{company_id}:{started_at}")
        self.rows["employments"].append(
            {
                "id": eid,
                "person_id": person_id,
                "company_id": company_id,
                "started_at": started_at.isoformat(),
                "ended_at": ended_at.isoformat() if ended_at else None,
            }
        )
        return eid

    def outsider(self, prefix: str = "outsider") -> str:
        """Посторонний человек: учредитель или директор чужой компании.

        Часть посторонних владеет несколькими компаниями (так и в ЕГРЮЛ), но не больше трёх:
        «номиналы» с 5+ компаниями заложены только в кейсах.
        """
        reusable = [p for p, n in self._outsider_load.items() if n < 3]
        if reusable and self.rng.random() < 0.42:
            pid = self.rng.choice(reusable)
        else:
            pid = self.person(self._key(prefix), self.random_name())
        self._outsider_load[pid] = self._outsider_load.get(pid, 0) + 1
        return pid

    def staff_company(
        self, cid: str, *, founder: str | None = None, director: str | None = None
    ) -> None:
        """Учредитель и директор по умолчанию — посторонние люди."""
        start = date.fromisoformat(self.companies[cid]["registered_at"])
        founder_id = founder or self.outsider()
        self.role(cid, founder_id, "founder", share=100.0, started_at=start)
        if director is not None:
            self.role(cid, director, "director", started_at=start)
        elif self.rng.random() < 0.55:
            self.role(cid, founder_id, "director", started_at=start)
        else:
            self.role(cid, self.outsider(), "director", started_at=start)

    # ------------------------------------------------------------------ contracts
    def contract(
        self,
        organ: str,
        company_id: str,
        amount: float,
        signed_at: date,
        group: str,
        method: str | None = None,
        key: str | None = None,
    ) -> str:
        year = signed_at.year
        self._contract_seq[(organ, year)] += 1
        reg = f"3{self.organ_inn[organ]}{year % 100:02d}{self._contract_seq[(organ, year)]:06d}"
        cid = stable_id("contract", key or reg)
        okpd2 = (
            f"{group}.{self.rng.choice([10, 11, 12, 19, 20, 21, 22])}.{self.rng.randint(110, 190)}"
        )
        self.rows["contracts"].append(
            {
                "id": cid,
                "reg_number": reg,
                "customer_organ_id": self.organ_ids[organ],
                "supplier_company_id": company_id,
                "amount": round(amount, 2),
                "signed_at": signed_at.isoformat(),
                "okpd2": okpd2,
                "method": method or self._method(amount),
            }
        )
        return cid

    def _method(self, amount: float) -> str:
        if amount < self.threshold:
            weights = (("single_supplier", 0.45), ("quotation", 0.35), ("auction", 0.2))
        else:
            weights = (
                ("auction", 0.72),
                ("tender", 0.13),
                ("quotation", 0.08),
                ("single_supplier", 0.07),
            )
        r = self.rng.random()
        acc = 0.0
        for method, weight in weights:
            acc += weight
            if r <= acc:
                return method
        return weights[-1][0]

    def amount(self, group: str, sigma: float = 0.55) -> float:
        median = vocab.OKPD2[group][2]
        value = median * math.exp(self.rng.gauss(0, sigma))
        # Не попадаем случайно в «чуть ниже порога» и не делаем «круглых» сумм.
        if 0.88 * self.threshold <= value < self.threshold:
            value *= 0.8
        value = round(value, 2)
        if value % 10_000 == 0:
            value += 137.5
        return value

    def contract_day(self, start: date = CONTRACTS_FROM, end: date = CONTRACTS_TO) -> date:
        return self._date(max(start, CONTRACTS_FROM), min(end, CONTRACTS_TO))
