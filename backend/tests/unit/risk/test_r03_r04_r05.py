from dataclasses import replace
from datetime import date

from src.modules.risk.domain.contacts import normalize_address, normalize_phone
from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import (
    AuthorityFacts,
    CompanyFacts,
    CompanyRoleFacts,
    EmploymentFacts,
    OfficialFacts,
    PersonFacts,
    RelativeFacts,
)
from src.modules.risk.domain.rules.r03_ex_employer_supplier import ExEmployerSupplierRule
from src.modules.risk.domain.rules.r04_revolving_door import RevolvingDoorRule
from src.modules.risk.domain.rules.r05_shared_contacts import (
    MASS_REGISTRATION_THRESHOLD,
    SharedContactsRule,
)
from src.modules.risk.domain.world import RiskWorld
from tests.unit.risk.conftest import (
    COMPANY_ID,
    OTHER_ORGAN_ID,
    make_company,
    make_contract,
    make_official,
    uid,
)

# --- R03: бывший работодатель — подрядчик органа --------------------------------------------


def _ex_employee(ended_at: date = date(2021, 2, 28)) -> OfficialFacts:
    official = make_official(with_spouse=False)  # назначен 01.03.2021
    return replace(
        official,
        employments=(EmploymentFacts(COMPANY_ID, date(2016, 1, 10), ended_at),),
    )


def test_r03_fires_when_ex_employer_supplies_organ_within_3_years(today: date) -> None:
    official = _ex_employee()
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        contracts=[make_contract("c1", date(2022, 5, 1)), make_contract("c2", date(2023, 9, 1))],
    )

    flags = ExEmployerSupplierRule().evaluate(official, world)

    assert [(f.rule_code, f.severity) for f in flags] == [(RuleCode.R03, Severity.MEDIUM)]
    assert "2 контракта" in flags[0].explanation
    assert [n.type for n in flags[0].evidence] == [
        NodeType.PERSON,
        NodeType.COMPANY,
        NodeType.CONTRACT,
        NodeType.CONTRACT,
        NodeType.ORGAN,
    ]


def test_r03_ignores_contracts_5_years_after_leaving(today: date) -> None:
    official = _ex_employee(ended_at=date(2019, 1, 1))
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        contracts=[make_contract("c1", date(2024, 6, 1))],
    )

    assert ExEmployerSupplierRule().evaluate(official, world) == []


def test_r03_ignores_ex_employer_supplying_another_organ(today: date) -> None:
    official = _ex_employee()
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        contracts=[make_contract("c1", date(2022, 5, 1), organ_id=OTHER_ORGAN_ID)],
    )

    assert ExEmployerSupplierRule().evaluate(official, world) == []


# --- R04: переход к подрядчику после увольнения ----------------------------------------------


def _former_official(left: date = date(2025, 6, 30)) -> OfficialFacts:
    official = make_official(with_spouse=False)
    return replace(
        official,
        appointments=tuple(replace(a, ended_at=left) for a in official.appointments),
    )


def test_r04_fires_when_former_official_joins_supplier(today: date) -> None:
    official = replace(
        _former_official(), employments=(EmploymentFacts(COMPANY_ID, date(2025, 10, 1)),)
    )
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        contracts=[make_contract("c1", date(2024, 3, 1))],
    )

    flags = RevolvingDoorRule().evaluate(official, world)

    assert [(f.rule_code, f.severity) for f in flags] == [(RuleCode.R04, Severity.MEDIUM)]
    assert "01.10.2025" in flags[0].explanation


def test_r04_counts_becoming_director_of_supplier(today: date) -> None:
    official = _former_official()
    role = CompanyRoleFacts(COMPANY_ID, official.person.id, "director", date(2026, 1, 15))
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        company_roles=[role],
        contracts=[make_contract("c1", date(2024, 3, 1))],
    )

    flags = RevolvingDoorRule().evaluate(official, world)

    assert len(flags) == 1 and "руководителем" in flags[0].explanation


def test_r04_ignores_move_more_than_2_years_later(today: date) -> None:
    official = replace(
        _former_official(left=date(2022, 1, 1)),
        employments=(EmploymentFacts(COMPANY_ID, date(2024, 6, 1)),),
    )
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        contracts=[make_contract("c1", date(2021, 6, 1))],
    )

    assert RevolvingDoorRule().evaluate(official, world) == []


def test_r04_ignores_company_without_contracts_during_tenure(today: date) -> None:
    official = replace(
        _former_official(), employments=(EmploymentFacts(COMPANY_ID, date(2025, 10, 1)),)
    )
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        contracts=[make_contract("c1", date(2025, 12, 1))],  # уже после увольнения
    )

    assert RevolvingDoorRule().evaluate(official, world) == []


def test_r04_ignores_acting_official(today: date) -> None:
    official = replace(
        make_official(with_spouse=False),
        employments=(EmploymentFacts(COMPANY_ID, date(2025, 10, 1)),),
    )
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        contracts=[make_contract("c1", date(2024, 3, 1))],
    )

    assert RevolvingDoorRule().evaluate(official, world) == []


# --- R05: общий адрес или телефон с подрядчиком ----------------------------------------------

MOTHER = PersonFacts(
    uid("mother"), "Белова Галина Петровна", address="г. Энск, ул. Мира, д. 3, кв. 7"
)


def _with_mother() -> OfficialFacts:
    return replace(make_official(with_spouse=False), relatives=(RelativeFacts(MOTHER, "parent"),))


def _supplier(*, address: str | None = None, phone: str | None = None) -> CompanyFacts:
    return replace(make_company(), address=address, phone=phone)


def test_r05_fires_when_supplier_address_matches_mothers(today: date) -> None:
    official = _with_mother()
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[_supplier(address="Энск, улица Мира, дом 3, офис 7")],
        contracts=[make_contract("c1", date(2024, 4, 1))],
    )

    flags = SharedContactsRule().evaluate(official, world)

    assert [(f.rule_code, f.severity) for f in flags] == [(RuleCode.R05, Severity.MEDIUM)]
    assert "Адрес" in flags[0].explanation and "родитель" in flags[0].explanation
    assert [n.id for n in flags[0].evidence[:3]] == [official.person.id, MOTHER.id, COMPANY_ID]


def test_r05_fires_on_shared_phone_in_other_format(today: date) -> None:
    in_law = PersonFacts(uid("brother-in-law"), "Кузнецов Олег Олегович", phone="8 (900) 555-44-33")
    official = replace(make_official(), relatives=(RelativeFacts(in_law, "in_law"),))
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[_supplier(phone="+7 900 5554433")],
        contracts=[make_contract("c1", date(2024, 4, 1))],
    )

    flags = SharedContactsRule().evaluate(official, world)

    assert len(flags) == 1 and "Телефон" in flags[0].explanation


def test_r05_suppresses_mass_registration_address(today: date) -> None:
    official = _with_mother()
    shared = "г. Энск, ул. Мира, д. 3, кв. 7"
    neighbours = [
        CompanyFacts(
            uid(f"shell-{i}"), f"ООО «Ромашка-{i}»", f"77{i:08d}", "active", address=shared
        )
        for i in range(MASS_REGISTRATION_THRESHOLD)
    ]
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[_supplier(address=shared), *neighbours],
        contracts=[make_contract("c1", date(2024, 4, 1))],
    )

    assert SharedContactsRule().evaluate(official, world) == []


def test_r05_ignores_company_that_is_not_a_supplier_during_tenure(today: date) -> None:
    official = _with_mother()
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[_supplier(address=MOTHER.address or "")],
        contracts=[make_contract("c1", date(2019, 4, 1))],  # до назначения
    )

    assert SharedContactsRule().evaluate(official, world) == []


def test_contacts_normalization() -> None:
    assert normalize_phone("+7 (900) 000-00-01") == normalize_phone("8 900 0000001")
    assert normalize_phone("12-34") is None
    assert normalize_address("г. Энск, ул. Ленина, д. 5, кв. 12") == normalize_address(
        "Энск, улица Ленина, дом 5, офис 12"
    )
    assert normalize_address("г. Энск, ул. Ленина, д. 5") != normalize_address(
        "г. Энск, ул. Ленина, д. 7"
    )


def test_r03_r05_need_authority_free_official_too(today: date) -> None:
    """R03 и R05 не требуют полномочия procurement: связь с подрядчиком важна сама по себе."""
    official = replace(
        _with_mother(),
        appointments=tuple(
            replace(a, authorities=(AuthorityFacts("permits"),))
            for a in _with_mother().appointments
        ),
    )
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[_supplier(address=MOTHER.address or "")],
        contracts=[make_contract("c1", date(2024, 4, 1))],
    )

    assert len(SharedContactsRule().evaluate(official, world)) == 1
