from dataclasses import replace
from datetime import date

from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import (
    AuthorityFacts,
    CompanyRoleFacts,
    ContractFacts,
    OfficialFacts,
)
from src.modules.risk.domain.flag import RiskFlag
from src.modules.risk.domain.rules.r01_relative_supplier import RelativeSupplierRule
from src.modules.risk.domain.world import RiskWorld
from tests.unit.risk.conftest import (
    OTHER_ORGAN_ID,
    make_company,
    make_contract,
    make_official,
    make_role,
    uid,
)


def _evaluate(
    official: OfficialFacts,
    roles: list[CompanyRoleFacts],
    contracts: list[ContractFacts],
    today: date,
) -> list[RiskFlag]:
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        company_roles=roles,
        contracts=contracts,
    )
    return RelativeSupplierRule().evaluate(official, world)


def test_r01_fires_when_spouse_company_gets_contracts_of_officials_organ(today: date) -> None:
    official = make_official()
    contracts = [make_contract("c1", date(2023, 4, 18)), make_contract("c2", date(2024, 2, 2))]

    flags = _evaluate(official, [make_role("spouse")], contracts, today)

    assert len(flags) == 1
    flag = flags[0]
    assert flag.rule_code is RuleCode.R01
    assert flag.severity is Severity.HIGH
    assert flag.legal_ref == "273-ФЗ ст. 10, 11"
    assert "2 контракта" in flag.explanation and "супруг(а)" in flag.explanation
    # цепочка: служащий -> супруга -> компания -> контракты -> орган
    assert [n.type for n in flag.evidence] == [
        NodeType.PERSON,
        NodeType.PERSON,
        NodeType.COMPANY,
        NodeType.CONTRACT,
        NodeType.CONTRACT,
        NodeType.ORGAN,
    ]


def test_r01_fires_for_officials_own_company(today: date) -> None:
    official = make_official(with_spouse=False)

    flags = _evaluate(
        official,
        [make_role("official", "director")],
        [make_contract("c1", date(2023, 4, 18))],
        today,
    )

    assert len(flags) == 1
    assert flags[0].evidence[1].type is NodeType.COMPANY


def test_r01_ignores_contracts_signed_before_appointment(today: date) -> None:
    official = make_official(started_at=date(2021, 3, 1))

    flags = _evaluate(
        official, [make_role("spouse")], [make_contract("c1", date(2020, 6, 1))], today
    )

    assert flags == []


def test_r01_ignores_contracts_of_another_organ(today: date) -> None:
    contract = make_contract("c1", date(2023, 4, 18), organ_id=OTHER_ORGAN_ID)

    assert _evaluate(make_official(), [make_role("spouse")], [contract], today) == []


def test_r01_ignores_okpd2_outside_authority_scope(today: date) -> None:
    contract = make_contract("c1", date(2023, 4, 18), okpd2="86.10")

    assert _evaluate(make_official(), [make_role("spouse")], [contract], today) == []


def test_r01_requires_procurement_authority(today: date) -> None:
    official = make_official(authorities=(AuthorityFacts("hr"),))

    flags = _evaluate(
        official, [make_role("spouse")], [make_contract("c1", date(2023, 4, 18))], today
    )

    assert flags == []


def test_r01_ignores_namesake_of_relative(today: date) -> None:
    """Полный тёзка супруги — учредитель: связь строится по person_id, а не по ФИО."""
    official = make_official()
    namesake = CompanyRoleFacts(
        company_id=make_company().id,
        person_id=uid("namesake"),
        role="founder",
        started_at=date(2018, 5, 14),
    )

    flags = _evaluate(official, [namesake], [make_contract("c1", date(2023, 4, 18))], today)

    assert flags == []


def test_r01_ignores_role_that_ended_before_contract(today: date) -> None:
    official = make_official()
    role = replace(make_role("spouse"), ended_at=date(2022, 12, 31))

    flags = _evaluate(official, [role], [make_contract("c1", date(2023, 4, 18))], today)

    assert flags == []


def test_r01_explanation_is_hedged_and_has_amount(today: date) -> None:
    official = make_official()

    flags = _evaluate(
        official, [make_role("spouse")], [make_contract("c1", date(2023, 4, 18))], today
    )

    assert "может свидетельствовать" in flags[0].explanation
    assert "8,4 млн" in flags[0].explanation
