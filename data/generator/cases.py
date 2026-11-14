"""Сценарий генерации: штат, фоновые закупки, демо-кейсы (data.md §4) и шум (§5).

Каждый кейс записывается в `_truth/schemes.json`: какие правила должны сработать на ком и
какие объекты образуют цепочку доказательств. Ложноположительные кейсы — с `rule_codes: []`.
"""

from datetime import date, timedelta
from typing import Any

from data.generator import vocab
from data.generator.ids import stable_id
from data.generator.names import FullName
from data.generator.world import (
    CONTRACTS_FROM,
    CONTRACTS_TO,
    MASS_ADDRESSES,
    Official,
    Scheme,
    WorldBuilder,
)

D = date.fromisoformat

PRIVATE_OKVED = ("62.01", "69.10", "69.20", "70.22", "47.11", "68.32", "85.41", "73.11", "56.10")


def fn(full: str) -> FullName:
    surname, name, patronymic = full.split()
    gender = "f" if patronymic.endswith("на") else "m"
    return FullName(surname, name, patronymic, gender)


class Scenario:
    def __init__(self, world: WorldBuilder) -> None:
        self.w = world
        self.rng = world.rng
        self.private: list[str] = []
        self.cases: dict[str, Official] = {}
        self.case_companies: dict[str, str] = {}
        self.case_contracts: dict[str, list[str]] = {}

    # ================================================================== entry point
    def build(self) -> None:
        w = self.w
        w.build_organs()
        self.private_companies()
        self.fixed_officials()
        self.fill_positions()
        self.former_officials()
        self.random_relatives()
        self.past_employments()
        self.background_contracts()
        self.demo_cases()
        self.extra_cases()
        self.noise_cases()

    # ================================================================== staff
    def fixed_officials(self) -> None:
        """Должности, на которых сидят кейсы. Остальные слоты заполняет fill_positions."""
        w = self.w
        plan: list[tuple[str, str, str, str, date, date | None, str | None]] = [
            # organ, position, case, ФИО (None — случайное), начало, конец, дата рождения
            ("O1", "proc_head", "H1", "Соколов Андрей Викторович", D("2021-02-01"), None, "1976-05-14"),
            ("O1", "proc_dep", "X1", "", D("2019-10-01"), None, None),
            ("O1", "proc_main", "R08-A", "", D("2020-03-02"), None, None),
            ("O1", "proc_lead", "X2", "", D("2022-04-04"), None, None),
            ("O1", "proc_exp", "C6", "Карпов Евгений Юрьевич", D("2022-05-16"), None, "1988-11-02"),
            ("O1", "proc_it", "N-R01-SCOPE", "", D("2018-06-01"), None, None),
            ("O1", "roads_main", "IVANOV-1", "Иванов Олег Петрович", D("2016-04-11"), None, "1979-03-21"),
            ("O1", "build_main", "IVANOV-2", "Иванов Дмитрий Сергеевич", D("2019-08-19"), None, "1987-07-30"),
            ("O1", "build_main", "N-R05-MASS-1", "", D("2017-01-16"), None, None),
            ("O1", "fin_head", "R02-B", "", D("2015-09-01"), None, None),
            ("O1", "build_head", "N-R02-LIQ-1", "", D("2016-02-01"), None, None),
            ("O1", "law_main", "N-R03-LATE-1", "", D("2021-03-01"), None, None),
            ("O1", "roads_head", "ROADS-NEW", "", D("2024-09-02"), None, None),
            ("O2", "proc_head", "C4-SUCCESSOR", "", D("2025-07-15"), None, None),
            ("O2", "proc_dep", "N-R06-MAKER", "", D("2016-05-04"), None, None),
            ("O2", "proc_main", "R01-CHILD", "", D("2017-02-01"), None, None),
            ("O2", "proc_exp", "R06-A", "", D("2019-01-15"), None, None),
            ("O2", "proc_it", "R08-B", "", D("2020-11-02"), None, None),
            ("O2", "lic_main", "C2", "Лебедева Ольга Николаевна", D("2018-09-03"), None, "1982-01-25"),
            ("O2", "lic_main", "N-R02-TRUST", "", D("2019-03-11"), None, None),
            ("O2", "lic_head", "LIC-NEW", "", D("2024-04-15"), None, None),
            ("O2", "ctrl_head", "R03-B", "", D("2022-12-12"), None, None),
            ("O2", "ctrl_main", "R05-PHONE", "", D("2018-02-05"), None, None),
            ("O2", "ctrl_exp", "TARASOV-1", "Тарасов Игорь Николаевич", D("2017-10-02"), None, "1985-02-11"),
            ("O2", "org_exp", "TARASOV-2", "Тарасов Алексей Юрьевич", D("2020-06-15"), None, "1991-09-09"),
            ("O2", "fin_head", "R02-C", "", D("2014-11-17"), None, None),
            ("O2", "fin_main", "N-R05-MASS-2", "", D("2016-08-22"), None, None),
            ("O2", "hr_head", "N-R02-LIQ-2", "", D("2013-05-06"), None, None),
            ("O2", "law_main", "N-R03-LATE-2", "", D("2020-01-20"), None, None),
            ("O3", "dep1", "C3", "Гусев Павел Сергеевич", D("2024-03-01"), None, "1980-08-08"),
            ("O3", "blag_head", "C5", "Белова Ирина Андреевна", D("2020-09-01"), None, "1984-04-17"),
            ("O3", "blag_main", "R01-INLAW", "", D("2018-04-02"), None, None),
            ("O3", "gkh_head", "R01-SPOUSE", "", D("2016-10-03"), None, None),
            ("O3", "gkh_main", "R06-B", "", D("2017-06-13"), None, None),
            ("O3", "gkh_lead", "R08-C", "", D("2019-12-02"), None, None),
            ("O3", "tech_exp", "N-R01-BEFORE", "", D("2025-02-03"), None, None),
            ("O3", "it_lead", "N-R01-NAMESAKE-2", "", D("2018-11-12"), None, None),
            ("O3", "gkh_spec", "N1", "Орлов Сергей Михайлович", D("2019-05-20"), None, "1983-12-03"),
            ("O3", "insp_head", "R05-ADDRESS", "", D("2017-03-14"), None, None),
            ("O3", "insp_main", "R03-C", "", D("2022-01-10"), None, None),
            ("O3", "fin_main", "N-R05-MASS-3", "", D("2015-07-01"), None, None),
        ]  # fmt: skip
        used: dict[tuple[str, str], int] = {}
        for organ, key, case, full, start, end, birth in plan:
            index = used.get((organ, key), 0)
            used[(organ, key)] = index + 1
            name = fn(full) if full else w.new_official_name()
            official = w.appoint(
                organ,
                key,
                name,
                person_key=f"case:{case}",
                started_at=start,
                ended_at=end,
                birth=D(birth) if birth else None,
                case=case,
            )
            w.slots[(organ, key, index)] = official
            self.cases[case] = official

    def fill_positions(self) -> None:
        w = self.w
        for organ, positions in vocab.POSITIONS.items():
            for key, _dept, _title, auths, holders in positions:
                scoped = any(kind == "procurement" and codes for kind, codes in auths)
                extra = 2 if holders >= 3 else (1 if holders == 2 else 0)
                for index in range(holders + extra):
                    if (organ, key, index) in w.slots:
                        continue
                    if scoped or auths:
                        start = w._date(D("2011-01-10"), D("2022-10-31"))
                    else:
                        start = w._date(D("2011-01-10"), D("2025-09-30"))
                    official = w.appoint(
                        organ,
                        key,
                        w.new_official_name(),
                        person_key=w._key("official:"),
                        started_at=start,
                    )
                    w.slots[(organ, key, index)] = official
                    if self.rng.random() < 0.18:
                        self._promotion_history(official)

    def _promotion_history(self, official: Official) -> None:
        """Прошлая должность в том же органе без полномочий: повышение."""
        w = self.w
        plain = [k for k, _d, _t, auths, _h in vocab.POSITIONS[official.organ] if not auths]
        key = self.rng.choice(plain)
        end = official.started_at - timedelta(days=1)
        start = end - timedelta(days=self.rng.randint(400, 2200))
        w.rows["appointments"].append(
            {
                "id": stable_id("appointment", f"history:{official.person_id}:{key}"),
                "person_id": official.person_id,
                "position_id": w.position_ids[(official.organ, key)],
                "started_at": start.isoformat(),
                "ended_at": end.isoformat(),
            }
        )

    def former_officials(self) -> None:
        """~15 бывших служащих: C4, два R04 и нейтральные (ушли к посторонним работодателям)."""
        w = self.w
        c4 = w.appoint(
            "O2",
            "proc_head",
            fn("Морозов Денис Игоревич"),
            person_key="case:C4",
            started_at=D("2019-04-01"),
            ended_at=D("2025-06-30"),
            birth=D("1978-10-05"),
            case="C4",
        )
        self.cases["C4"] = c4
        self.cases["R04-A"] = w.appoint(
            "O1", "roads_head", w.new_official_name(), person_key="case:R04-A",
            started_at=D("2016-03-01"), ended_at=D("2024-08-16"), case="R04-A",
        )  # fmt: skip
        self.cases["R04-B"] = w.appoint(
            "O2", "lic_head", w.new_official_name(), person_key="case:R04-B",
            started_at=D("2014-02-03"), ended_at=D("2024-03-29"), case="R04-B",
        )  # fmt: skip
        self.cases["C3-PREDECESSOR"] = w.appoint(
            "O3", "dep1", w.new_official_name(), person_key="case:C3-PREDECESSOR",
            started_at=D("2015-04-06"), ended_at=D("2024-02-20"), case="C3-PREDECESSOR",
        )  # fmt: skip
        plain = [
            (organ, key)
            for organ, positions in vocab.POSITIONS.items()
            for key, _d, _t, auths, holders in positions
            if holders > 1
        ]
        for _ in range(11):
            organ, key = self.rng.choice(plain)
            end = w._date(D("2018-01-15"), D("2025-08-29"))
            start = end - timedelta(days=self.rng.randint(700, 3000))
            official = w.appoint(
                organ, key, w.new_official_name(), person_key=w._key("former:"),
                started_at=start, ended_at=end,
            )  # fmt: skip
            if self.rng.random() < 0.6:
                company = self.rng.choice(self.active_private())
                w.employment(
                    official.person_id,
                    company,
                    end + timedelta(days=self.rng.randint(20, 500)),
                    None,
                )

    def random_relatives(self) -> None:
        w = self.w
        kinds = [k for k, _ in vocab.KINSHIP_WEIGHTS]
        weights = [p for _, p in vocab.KINSHIP_WEIGHTS]
        for official in list(w.officials.values()):
            count = self.rng.choices([0, 1, 2, 3, 4, 5], [0.08, 0.2, 0.3, 0.24, 0.12, 0.06])[0]
            has_spouse = False
            for _ in range(count):
                kind = self.rng.choices(kinds, weights)[0]
                if kind == "spouse":
                    if has_spouse:
                        kind = "child"
                    has_spouse = True
                same_home = kind == "spouse" or (kind == "child" and self.rng.random() < 0.4)
                w.relative(official, kind, address=official.address if same_home else None)

    def private_companies(self) -> None:
        """Посторонние работодатели без контрактов с органами (для истории занятости)."""
        w = self.w
        for i in range(64):
            status = "active"
            if i % 2 == 0:
                status = "liquidated"
            elif i % 15 == 1:
                status = "liquidating"
            cid = w.company(f"private:{i}", okved=self.rng.choice(PRIVATE_OKVED), status=status)
            w.staff_company(cid)
            self.private.append(cid)

    def active_private(self) -> list[str]:
        return [c for c in self.private if self.w.companies[c]["status"] == "active"]

    def past_employments(self) -> None:
        """Прошлые места работы служащих — только у посторонних работодателей (R03 молчит)."""
        w = self.w
        for official in list(w.officials.values()):
            if official.case and official.case.startswith(("R03", "X2", "C3", "C4", "N-R03")):
                continue
            jobs = self.rng.choices([0, 1, 2, 3], [0.08, 0.37, 0.38, 0.17])[0]
            end = official.started_at - timedelta(days=self.rng.randint(5, 400))
            for _ in range(jobs):
                start = end - timedelta(days=self.rng.randint(300, 2500))
                w.employment(official.person_id, self.rng.choice(self.private), start, end)
                end = start - timedelta(days=self.rng.randint(10, 300))

    # ================================================================== background procurement
    def background_contracts(self) -> None:
        w = self.w
        demand: dict[str, int] = {}
        for organ_groups in vocab.GROUP_CONTRACTS.values():
            for group, count in organ_groups.items():
                demand[group] = demand.get(group, 0) + count
        mass_suppliers = self._mass_registration()
        for group, total in demand.items():
            size = max(7, min(12, total // 8))
            okved = vocab.OKPD2[group][1]
            pool = []
            for i in range(size):
                cid = w.company(f"supplier:{group}:{i}", okved=okved)
                w.staff_company(cid)
                pool.append(cid)
            for organ in vocab.ORGANS:
                if group in vocab.GROUP_CONTRACTS[organ]:
                    w.suppliers[(organ, group)] = list(pool)
        for organ, group in (("O1", "43.99"), ("O2", "86.90"), ("O3", "81.30")):
            w.suppliers[(organ, group)].append(mass_suppliers[organ])
        for organ, groups in vocab.GROUP_CONTRACTS.items():
            for group, count in groups.items():
                pool = w.suppliers[(organ, group)]
                weights = [self.rng.uniform(0.6, 1.4) for _ in pool]
                for _ in range(round(count * 1.12)):
                    supplier = self.rng.choices(pool, weights)[0]
                    w.contract(organ, supplier, w.amount(group), w.contract_day(), group)
                # Компании массовой регистрации гарантированно поставляют (шум R05).
                if pool[-1] in mass_suppliers.values():
                    for day in (D("2023-06-14"), D("2025-04-22")):
                        w.contract(organ, pool[-1], w.amount(group), day, group)

    def _mass_registration(self) -> dict[str, str]:
        """Два адреса массовой регистрации (12 и 9 компаний): R05 их подавляет."""
        w = self.w
        suppliers: dict[str, str] = {}
        for idx, (address, count) in enumerate(zip(MASS_ADDRESSES, (12, 9), strict=True)):
            w._address(value=address)
            for i in range(count):
                okved = self.rng.choice(("43.99", "86.90", "81.30", "70.22", "46.49"))
                cid = w.company(f"mass:{idx}:{i}", okved=okved, address=address)
                w.staff_company(cid)
                if idx == 0 and i == 0:
                    suppliers["O1"] = cid
                if idx == 0 and i == 1:
                    suppliers["O2"] = cid
                if idx == 1 and i == 0:
                    suppliers["O3"] = cid
        return suppliers

    # ================================================================== demo cases (data.md §4)
    def demo_cases(self) -> None:
        self._h1()
        self._c2()
        self._c3()
        self._c4()
        self._c5()
        self._c6()
        n1 = self.cases["N1"]
        self.scheme("N1", ["R07"], n1, [n1.person_id], "Чистый служащий: одно эмоциональное "
                    "обращение без фактов (ложное обвинение) даёт только R07 low.")  # fmt: skip

    def _h1(self) -> None:
        w = self.w
        h1 = self.cases["H1"]
        wife = w.relative(
            h1, "spouse", fn("Соколова Марина Олеговна"), key="case:H1:wife",
            address=h1.address, birth=D("1979-02-09"),
        )  # fmt: skip
        in_law_phone = w._phone("+7 912 455-17-39")
        brother = w.relative(
            h1, "in_law", fn("Кравцов Игорь Олегович"), key="case:H1:wife-brother",
            phone=in_law_phone, birth=D("1982-06-30"),
        )  # fmt: skip
        nominee = w.person(
            "case:H1:nominee", fn("Ершов Константин Леонидович"), birth=D("1969-01-17")
        )
        company = w.company(
            "case:H1:dsr", name="ООО «ДорСтройРесурс»", okved="42.11",
            registered_at=D("2024-09-16"), phone="8 (912) 455-17-39",
        )  # fmt: skip
        w.role(company, wife, "founder", share=100.0, started_at=D("2024-09-16"))
        w.role(company, nominee, "director", started_at=D("2024-09-16"))
        # Номинальный директор ещё шести компаний.
        for i in range(6):
            other = w.company(f"case:H1:nominee-co:{i}", okved=self.rng.choice(("43.99", "46.73", "41.20")),
                              registered_at=w._date(D("2019-01-01"), D("2024-06-01")))  # fmt: skip
            w.role(other, w.outsider(), "founder", share=100.0)
            w.role(other, nominee, "director")
        contracts = [
            ("2025-01-20", 7_000_000, "single_supplier"),
            ("2025-05-14", 8_000_000, "auction"),
            ("2025-09-03", 6_000_000, "single_supplier"),
            ("2026-03-17", 9_500_000, "single_supplier"),
            ("2026-07-08", 7_500_000, "quotation"),
        ]
        ids = [
            w.contract("O1", company, amount, D(day), "42.11", method, key=f"H1:{day}")
            for day, amount, method in contracts
        ]
        self.case_companies["H1"] = company
        self.case_contracts["H1"] = ids
        self.scheme(
            "H1", ["R01", "R05", "R06", "R07"], h1,
            [h1.person_id, wife, company, *ids, w.organ_ids["O1"], brother, nominee],
            "Супруга — учредитель ООО «ДорСтройРесурс» (за 4 мес. до первого контракта), "
            "директор-номинал Ершов К. Л. (7 компаний), 5 контрактов O1 на 38 млн ₽, 3 у "
            "единственного поставщика; телефон ООО = телефон брата супруги; доля ООО в 42.11 ~60 %.",
        )  # fmt: skip

    def _c2(self) -> None:
        w = self.w
        c2 = self.cases["C2"]
        company = w.company("case:C2:mts", name="ООО «МедТехСнаб»", okved="46.69",
                            registered_at=D("2015-03-12"))  # fmt: skip
        w.role(company, c2.person_id, "founder", share=60.0, started_at=D("2015-03-12"))
        w.role(company, c2.person_id, "director", started_at=D("2015-03-12"))
        w.role(company, w.outsider(), "founder", share=40.0, started_at=D("2015-03-12"))
        self.scheme("C2", ["R02"], c2, [c2.person_id, company, w.organ_ids["O2"]],
                    "Учредитель и директор действующего ООО «МедТехСнаб».")  # fmt: skip

    def _c3(self) -> None:
        w = self.w
        c3 = self.cases["C3"]
        company = w.company("case:C3:gks", name="ООО «ЖилКомСервис»", okved="43.22",
                            registered_at=D("2009-07-01"))  # fmt: skip
        w.staff_company(company)
        w.employment(c3.person_id, company, D("2016-05-16"), D("2024-02-28"))
        w.employment(c3.person_id, self.rng.choice(self.private), D("2010-09-01"), D("2016-05-06"))
        ids = []
        for i in range(11):
            day = w._date(D("2024-04-01"), D("2026-10-15"))
            ids.append(w.contract("O3", company, w.amount("43.22"), day, "43.22", key=f"C3:{i}"))
        self.scheme("C3", ["R03"], c3, [c3.person_id, company, *ids, w.organ_ids["O3"]],
                    "До назначения (03.2024) работал в ООО «ЖилКомСервис»; с 2024 года у ООО "
                    "11 контрактов с O3.")  # fmt: skip

    def _c4(self) -> None:
        w = self.w
        c4 = self.cases["C4"]
        company = w.company("case:C4:pl", name="ООО «ФармЛогистик»", okved="46.46",
                            registered_at=D("2012-02-20"))  # fmt: skip
        w.staff_company(company)
        w.employment(c4.person_id, company, D("2025-10-06"), None)
        w.employment(
            c4.person_id, self.rng.choice(self.active_private()), D("2011-03-01"), D("2019-03-15")
        )
        days = ["2023-03-15", "2023-08-02", "2024-01-24", "2024-05-30", "2024-10-09",
                "2025-02-18", "2025-05-27"]  # fmt: skip
        ids = [
            w.contract("O2", company, w.amount("21.20"), D(day), "21.20", key=f"C4:{day}")
            for day in days
        ]
        self.scheme("C4", ["R04"], c4, [c4.person_id, company, *ids, w.organ_ids["O2"]],
                    "Уволился 06.2025, с 10.2025 — заместитель директора ООО «ФармЛогистик», "
                    "получившего при нём 7 контрактов O2.")  # fmt: skip

    def _c5(self) -> None:
        w = self.w
        c5 = self.cases["C5"]
        mother_address = w._address(value="г. Энск, ул. Садовая, д. 14, кв. 7")
        mother = w.relative(c5, "parent", fn("Белова Галина Петровна"), key="case:C5:mother",
                            address=mother_address, birth=D("1957-10-21"))  # fmt: skip
        company = w.company("case:C5:cd", name="ООО «Чистый Двор»", okved="81.29",
                            registered_at=D("2019-11-05"), address=mother_address)  # fmt: skip
        w.staff_company(company)
        ids = []
        for i in range(14):
            day = w._date(D("2023-02-01"), D("2026-09-30"))
            amount = 1_600_000 * self.rng.uniform(0.85, 1.15)
            ids.append(w.contract("O3", company, amount, day, "81.29", key=f"C5:{i}"))
        self.scheme("C5", ["R05", "R06"], c5,
                    [c5.person_id, mother, company, *ids, w.organ_ids["O3"]],
                    "Адрес ООО «Чистый Двор» совпадает с адресом матери; доля ООО ~65 % по 81.29.")  # fmt: skip

    def _c6(self) -> None:
        w = self.w
        c6 = self.cases["C6"]
        features = self._anomalous_contracts(
            c6, "33.12", count=24, near_threshold=True, young=True, key="C6"
        )
        self.scheme("C6", ["R08"], c6, [c6.person_id, w.organ_ids["O1"]],
                    "Правила молчат: 40 % закупок чуть ниже порога, поставщики зарегистрированы "
                    "менее чем за 3 месяца до контракта.")  # fmt: skip
        self.peer(c6, features)

    def _anomalous_contracts(
        self,
        official: Official,
        group: str,
        *,
        count: int,
        key: str,
        near_threshold: bool = False,
        young: bool = False,
        round_amounts: bool = False,
        single: bool = False,
        nominee: bool = False,
    ) -> list[str]:
        """Контракты-аномалии в сфере служащего: каждый поставщик берёт 1–2 контракта (R06 молчит)."""
        w = self.w
        director = w.person(f"case:{key}:nominee", w.random_name("m")) if nominee else None
        if director is not None:
            for i in range(5):
                other = w.company(f"case:{key}:nominee-extra:{i}", okved="70.22")
                w.role(other, w.outsider(), "founder", share=100.0)
                w.role(other, director, "director")
        start = max(official.started_at, CONTRACTS_FROM)
        made = 0
        index = 0
        while made < count:
            first = w._date(start + timedelta(days=100), CONTRACTS_TO - timedelta(days=60))
            registered = first - timedelta(days=self.rng.randint(25, 85)) if young else None
            company = w.company(
                f"case:{key}:supplier:{index}",
                okved=vocab.OKPD2[group][1],
                registered_at=registered,
            )
            w.staff_company(company, director=director)
            for j in range(min(self.rng.choice((1, 2, 2)), count - made)):
                day = first + timedelta(days=40 * j)
                if near_threshold:
                    amount = w.threshold * self.rng.uniform(0.905, 0.995)
                elif round_amounts:
                    amount = float(self.rng.choice((300, 400, 500, 700, 800, 900, 1200)) * 1000)
                else:
                    amount = w.amount(group)
                method = "single_supplier" if single or amount < w.threshold else None
                w.contract(official.organ, company, amount, day, group, method,
                           key=f"{key}:{index}:{j}")  # fmt: skip
                made += 1
            index += 1
        features = []
        if near_threshold:
            features.append("share_near_threshold")
        if young:
            features.append("young_supplier_share")
        if round_amounts:
            features.append("share_round_amounts")
        if single:
            features.append("share_single_supplier")
        if nominee:
            features.append("nominee_director_share")
        return features

    # ================================================================== extra positives
    def extra_cases(self) -> None:
        w = self.w
        # --- R01 + R02: X1 — супруга директор подрядчика, сам руководит своей фирмой.
        x1 = self.cases["X1"]
        wife = w.relative(x1, "spouse", key="case:X1:spouse")
        company = self._relative_supplier(x1, wife, "director", "41.20", 4, "X1")
        own = w.company("case:X1:own", okved="68.32", registered_at=D("2012-04-10"))
        w.role(own, x1.person_id, "founder", share=100.0)
        w.role(own, x1.person_id, "director")
        self.scheme("X1", ["R01", "R02"], x1, [x1.person_id, wife, company, own],
                    "Супруга — директор подрядчика O1 по 41.20; служащий руководит своим ООО.")  # fmt: skip

        # --- R01 + R05 + R03: X2 — брат учредитель подрядчика, телефон брата = телефон ООО;
        # бывший работодатель — тоже подрядчик.
        x2 = self.cases["X2"]
        phone = w._phone()
        brother = w.relative(x2, "sibling", key="case:X2:sibling", phone=phone)
        company = self._relative_supplier(x2, brother, "founder", "71.12", 5, "X2", phone=phone)
        employer = w.company("case:X2:employer", okved="08.12", registered_at=D("2011-05-05"))
        w.staff_company(employer)
        w.employment(x2.person_id, employer, D("2015-02-02"), D("2022-03-25"))
        ex_ids = [
            w.contract(
                "O1",
                employer,
                w.amount("08.12"),
                w._date(D("2023-02-01"), D("2025-03-01")),
                "08.12",
                key=f"X2:employer:{i}",
            )  # fmt: skip
            for i in range(4)
        ]
        self.scheme("X2", ["R01", "R03", "R05"], x2,
                    [x2.person_id, brother, company, employer, *ex_ids],
                    "Брат — учредитель подрядчика по 71.12, общий телефон; бывший работодатель "
                    "поставляет щебень в O1.")  # fmt: skip

        for case, kind, role, group, count in (
            ("R01-CHILD", "child", "founder", "86.90", 6),
            ("R01-INLAW", "in_law", "founder", "81.30", 3),
            ("R01-SPOUSE", "spouse", "founder", "43.22", 7),
        ):
            official = self.cases[case]
            relative = w.relative(official, kind, key=f"case:{case}:relative")
            company = self._relative_supplier(official, relative, role, group, count, case)
            self.scheme(case, ["R01"], official, [official.person_id, relative, company],
                        f"Родственник ({kind}) — {role} подрядчика органа в сфере {group}.")  # fmt: skip

        # --- R02: директор и учредитель+директор действующих компаний.
        for case, roles in (("R02-B", ("director",)), ("R02-C", ("founder", "director"))):
            official = self.cases[case]
            company = w.company(f"case:{case}:own", okved=self.rng.choice(PRIVATE_OKVED))
            if "founder" in roles:
                w.role(company, official.person_id, "founder", share=50.0)
                w.role(company, w.outsider(), "founder", share=50.0)
            else:
                w.role(company, w.outsider(), "founder", share=100.0)
            w.role(company, official.person_id, "director")
            self.scheme(case, ["R02"], official, [official.person_id, company],
                        "Руководит действующей коммерческой организацией.")  # fmt: skip

        # --- R03: бывший работодатель в пределах 3 лет.
        for case, organ, group, left, window in (
            ("R03-B", "O2", "86.90", D("2022-11-30"), (D("2023-02-01"), D("2025-06-30"))),
            ("R03-C", "O3", "81.30", D("2021-12-24"), (D("2023-01-20"), D("2024-11-30"))),
        ):
            official = self.cases[case]
            employer = w.company(f"case:{case}:employer", okved=vocab.OKPD2[group][1],
                                 registered_at=D("2010-03-03"))  # fmt: skip
            w.staff_company(employer)
            w.employment(official.person_id, employer, left - timedelta(days=2400), left)
            ids = [
                w.contract(
                    organ, employer, w.amount(group), w._date(*window), group, key=f"{case}:{i}"
                )  # fmt: skip
                for i in range(5)
            ]
            self.scheme(case, ["R03"], official, [official.person_id, employer, *ids],
                        "Бывший работодатель (ушёл менее 3 лет назад) — подрядчик органа.")  # fmt: skip

        # --- R04: переход к подрядчику в течение 2 лет после увольнения.
        for case, organ, group, start in (
            ("R04-A", "O1", "43.99", D("2025-01-13")),
            ("R04-B", "O2", "32.50", D("2024-10-01")),
        ):
            official = self.cases[case]
            company = w.company(f"case:{case}:company", okved=vocab.OKPD2[group][1],
                                registered_at=D("2013-06-06"))  # fmt: skip
            w.staff_company(company)
            ids = [
                w.contract(
                    organ,
                    company,
                    w.amount(group),
                    w._date(D("2023-02-01"), (official.ended_at or CONTRACTS_TO)),
                    group,
                    key=f"{case}:{i}",
                )  # fmt: skip
                for i in range(4)
            ]
            w.employment(official.person_id, company, start, None)
            self.scheme(case, ["R04"], official, [official.person_id, company, *ids],
                        "После увольнения перешёл в компанию, получавшую контракты органа.")  # fmt: skip

        # --- R05: телефон матери и адрес сестры совпадают с подрядчиком органа.
        r05 = self.cases["R05-PHONE"]
        phone = w._phone()
        mother = w.relative(r05, "parent", key="case:R05-PHONE:mother", phone=phone)
        company = w.company("case:R05-PHONE:company", okved="86.90", phone=phone,
                            registered_at=D("2016-01-20"))  # fmt: skip
        w.staff_company(company)
        ids = [w.contract("O2", company, w.amount("86.90"), w.contract_day(), "86.90",
                          key=f"R05-PHONE:{i}") for i in range(3)]  # fmt: skip
        self.scheme("R05-PHONE", ["R05"], r05, [r05.person_id, mother, company, *ids],
                    "Телефон матери совпадает с телефоном подрядчика органа.")  # fmt: skip

        r05a = self.cases["R05-ADDRESS"]
        address = w._address()
        sister = w.relative(r05a, "sibling", key="case:R05-ADDRESS:sibling", address=address)
        company = w.company("case:R05-ADDRESS:company", okved="38.11",
                            address=address.replace("кв.", "оф."), registered_at=D("2017-08-08"))  # fmt: skip
        w.staff_company(company)
        ids = [w.contract("O3", company, w.amount("38.11"), w.contract_day(), "38.11",
                          key=f"R05-ADDRESS:{i}") for i in range(3)]  # fmt: skip
        self.scheme("R05-ADDRESS", ["R05"], r05a, [r05a.person_id, sister, company, *ids],
                    "Адрес сестры совпадает с адресом подрядчика органа.")  # fmt: skip

        # --- R06: доля одного поставщика > 60 % в сфере полномочий.
        for case, group, count, amount in (("R06-A", "33.13", 10, 3_100_000),
                                           ("R06-B", "42.21", 12, 8_200_000)):  # fmt: skip
            official = self.cases[case]
            company = w.company(f"case:{case}:dominant", okved=vocab.OKPD2[group][1],
                                registered_at=D("2014-09-09"))  # fmt: skip
            w.staff_company(company)
            ids = [
                w.contract(
                    official.organ,
                    company,
                    amount * self.rng.uniform(0.9, 1.1),
                    w.contract_day(),
                    group,
                    key=f"{case}:{i}",
                )  # fmt: skip
                for i in range(count)
            ]
            self.scheme(case, ["R06"], official, [official.person_id, company, *ids],
                        f"Один поставщик забирает больше 60 % закупок по {group}.")  # fmt: skip

        # --- R08: аномалии признаков без срабатывания правил.
        for case, group, kwargs in (
            ("R08-A", "43.99", {"young": True, "single": True}),
            ("R08-B", "26.20", {"round_amounts": True, "single": True}),
            ("R08-C", "38.11", {"near_threshold": True, "nominee": True}),
        ):
            official = self.cases[case]
            features = self._anomalous_contracts(official, group, count=16, key=case, **kwargs)
            self.scheme(case, ["R08"], official, [official.person_id],
                        "Признаки закупок аномальны относительно коллег: " + ", ".join(features))  # fmt: skip
            self.peer(official, features)

    def _relative_supplier(
        self,
        official: Official,
        relative: str,
        role: str,
        group: str,
        count: int,
        key: str,
        phone: str | None = None,
    ) -> str:
        w = self.w
        start = max(official.started_at, CONTRACTS_FROM) + timedelta(days=30)
        company = w.company(f"case:{key}:company", okved=vocab.OKPD2[group][1], phone=phone,
                            registered_at=start - timedelta(days=self.rng.randint(200, 900)))  # fmt: skip
        registered = w.companies[company]["registered_at"]
        if role == "founder":
            w.role(company, relative, "founder", share=100.0, started_at=D(registered))
            w.role(company, w.outsider(), "director", started_at=D(registered))
        else:
            w.role(company, w.outsider(), "founder", share=100.0, started_at=D(registered))
            w.role(company, relative, "director", started_at=D(registered))
        ids = [
            w.contract(
                official.organ,
                company,
                w.amount(group),
                w.contract_day(start),
                group,
                key=f"{key}:{i}",
            )  # fmt: skip
            for i in range(count)
        ]
        self.case_contracts[key] = ids
        self.case_companies[key] = company
        return company

    # ================================================================== noise (data.md §5)
    def noise_cases(self) -> None:
        w = self.w
        # Компания родственника — вне ОКПД2 полномочий или в другом органе.
        for case, target_organ, group, note in (
            ("N-R01-SCOPE", "O1", "43.99", "компания супруги поставляет в O1 вне ОКПД2 служащего"),
            ("N-R06-MAKER", "O1", "41.20", "компания брата поставляет в другой орган (O1)"),
            ("R08-B", "O3", "81.30", "компания сына поставляет в другой орган (O3)"),
            ("N-R01-NAMESAKE-2", "O2", "21.20", "компания супруги поставляет в другой орган (O2)"),
        ):
            official = self.cases[case]
            kind = {"N-R06-MAKER": "sibling", "R08-B": "child"}.get(case, "spouse")
            relative = w.relative(official, kind, key=f"noise:{case}:relative")
            company = w.company(f"noise:{case}:company", okved=vocab.OKPD2[group][1])
            w.role(company, relative, "founder", share=100.0)
            w.role(company, w.outsider(), "director")
            for i in range(3):
                w.contract(target_organ, company, w.amount(group), w.contract_day(), group,
                           key=f"noise:{case}:{i}")  # fmt: skip
            self.scheme(f"N-R01-OUT-{case}", [], official, [official.person_id, relative, company],
                        f"R01 не срабатывает: {note}.")  # fmt: skip

        # Контракты компании родственника заключены до назначения служащего.
        for case, group in (("C4-SUCCESSOR", "52.10"), ("N-R01-BEFORE", "33.12")):
            official = self.cases[case]
            relative = w.relative(official, "spouse", key=f"noise:{case}:before")
            company = w.company(f"noise:{case}:before-company", okved=vocab.OKPD2[group][1])
            w.role(company, relative, "founder", share=100.0)
            w.role(company, w.outsider(), "director")
            for i in range(3):
                day = w._date(D("2023-02-01"), official.started_at - timedelta(days=30))
                w.contract(official.organ, company, w.amount(group), day, group,
                           key=f"noise:{case}:before:{i}")  # fmt: skip
            self.scheme(f"N-R01-BEFORE-{case}", [], official,
                        [official.person_id, relative, company],
                        "R01 не срабатывает: контракты заключены до назначения служащего.")  # fmt: skip

        # Учредитель ликвидированной компании.
        for case in ("N-R02-LIQ-1", "N-R02-LIQ-2"):
            official = self.cases[case]
            company = w.company(f"noise:{case}:liq", okved=self.rng.choice(PRIVATE_OKVED),
                                status="liquidated")  # fmt: skip
            w.role(company, official.person_id, "founder", share=100.0)
            w.role(company, official.person_id, "director")
            self.scheme(case, [], official, [official.person_id, company],
                        "R02 не срабатывает: компания ликвидирована.")  # fmt: skip

        # Владеет долей, но не руководит: R02 medium с пометкой о доверительном управлении.
        trust = self.cases["N-R02-TRUST"]
        company = w.company("noise:N-R02-TRUST:company", okved="47.11")
        w.role(company, trust.person_id, "founder", share=35.0)
        w.role(company, w.outsider(), "founder", share=65.0)
        w.role(company, w.outsider(), "director")
        self.scheme("N-R02-TRUST", ["R02"], trust, [trust.person_id, company],
                    "Только учредитель (35 %), не руководит: R02 medium, проверить передачу доли "
                    "в доверительное управление.")  # fmt: skip

        # Бывший работодатель стал подрядчиком через 5+ лет после увольнения.
        for case, group in (("N-R03-LATE-1", "41.20"), ("N-R03-LATE-2", "32.50")):
            official = self.cases[case]
            employer = w.company(f"noise:{case}:employer", okved=vocab.OKPD2[group][1],
                                 registered_at=D("2006-04-04"))  # fmt: skip
            w.staff_company(employer)
            w.employment(official.person_id, employer, D("2011-09-01"), D("2017-10-31"))
            for i in range(3):
                w.contract(official.organ, employer, w.amount(group),
                           w._date(D("2023-01-15"), D("2026-09-30")), group,
                           key=f"noise:{case}:{i}")  # fmt: skip
            self.scheme(case, [], official, [official.person_id, employer],
                        "R03 не срабатывает: от увольнения до контрактов больше 5 лет.")  # fmt: skip

        # Общий адрес — адрес массовой регистрации.
        for case, address in (("N-R05-MASS-1", MASS_ADDRESSES[0]), ("N-R05-MASS-2", MASS_ADDRESSES[0]),
                              ("N-R05-MASS-3", MASS_ADDRESSES[1])):  # fmt: skip
            official = self.cases[case]
            relative = w.relative(official, "child", key=f"noise:{case}:child", address=address)
            self.scheme(case, [], official, [official.person_id, relative],
                        "R05 подавлен: совпадение с адресом массовой регистрации.")  # fmt: skip

        # Полный тёзка родственника — учредитель подрядчика (другие дата рождения и ИНН).
        for case, group in (("N-R01-SCOPE", "26.20"), ("N-R01-NAMESAKE-2", "58.29")):
            official = self.cases[case]
            rel_name = w.random_name("f")
            relative = w.relative(official, "sibling", rel_name, key=f"noise:{case}:namesake-rel",
                                  birth=D("1981-01-01"))  # fmt: skip
            namesake = w.person(f"noise:{case}:namesake", rel_name, birth=D("1993-07-07"),
                                allow_duplicate_name=True)  # fmt: skip
            company = w.company(f"noise:{case}:namesake-company", okved=vocab.OKPD2[group][1])
            w.role(company, namesake, "founder", share=100.0)
            w.role(company, namesake, "director")
            for i in range(3):
                w.contract(official.organ, company, w.amount(group), w.contract_day(), group,
                           key=f"noise:{case}:namesake:{i}")  # fmt: skip
            self.scheme(f"N-R01-NAMESAKE-{case}", [], official,
                        [official.person_id, relative, namesake, company],
                        "R01 не срабатывает: учредитель — полный тёзка родственника, другой человек.")  # fmt: skip

        # Единственный производитель: высокая доля по объективным причинам — только R06 low.
        maker_official = self.cases["N-R06-MAKER"]
        maker = w.company("noise:N-R06-MAKER:maker", name="АО «ЭнскМедПрибор»", okved="32.50",
                          registered_at=D("1998-03-03"))  # fmt: skip
        w.staff_company(maker)
        for i in range(10):
            w.contract("O2", maker, 13_000_000 * self.rng.uniform(0.9, 1.1), w.contract_day(),
                       "32.50", "tender", key=f"noise:maker:{i}")  # fmt: skip
        self.scheme("N-R06-MAKER", ["R06"], maker_official, [maker_official.person_id, maker],
                    "Крупный единственный производитель: R06 low без других флагов.")  # fmt: skip

        # Однофамильцы среди служащих: в обращении по фамилии — только кандидаты.
        for case in ("IVANOV-1", "IVANOV-2", "TARASOV-1", "TARASOV-2"):
            official = self.cases[case]
            self.scheme(case, [], official, [official.person_id],
                        "Однофамилец в том же органе: обращение по фамилии не привязывается.")  # fmt: skip

    # ================================================================== truth helpers
    def scheme(
        self, case_id: str, rules: list[str], official: Official, evidence: list[str], note: str
    ) -> None:
        self.w.schemes.append(Scheme(case_id, rules, official.person_id, evidence, note))

    def peer(self, official: Official, features: list[str]) -> None:
        self.w.peer_anomalies.append({"person_id": official.person_id, "features": features})

    def truth(self) -> dict[str, Any]:
        return {
            "schemes": [s.__dict__ for s in self.w.schemes],
            "peer_anomalies": self.w.peer_anomalies,
        }
