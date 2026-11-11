from dataclasses import replace
from datetime import date

from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import AuthorityFacts, CompanyFacts, ContractFacts
from src.modules.risk.domain.rules.r06_supplier_concentration import SupplierConcentrationRule
from src.modules.risk.domain.world import RiskWorld
from tests.unit.risk.conftest import COMPANY_ID, ORGAN_ID, make_company, make_official, uid

OTHER = CompanyFacts(uid("other-supplier"), "ООО «Конкурент»", "7703000000", "active")
CLEANING = (AuthorityFacts("procurement", ("81.29",)),)


def _contract(
    key: str, supplier: CompanyFacts, amount: float, okpd2: str = "81.29.12"
) -> ContractFacts:
    return ContractFacts(uid(key), key, ORGAN_ID, supplier.id, amount, date(2024, 5, 1), okpd2)


def _world(contracts: list[ContractFacts], today: date) -> RiskWorld:
    official = make_official(authorities=CLEANING, with_spouse=False)
    return RiskWorld(
        today=today, officials=[official], companies=[make_company(), OTHER], contracts=contracts
    )


def test_r06_fires_when_one_supplier_takes_65_percent(today: date) -> None:
    supplier = make_company()
    contracts = [_contract(f"a{i}", supplier, 13_000_000) for i in range(5)]
    contracts += [_contract(f"b{i}", OTHER, 7_000_000) for i in range(5)]
    world = _world(contracts, today)
    official = next(iter(world.officials.values()))

    flags = SupplierConcentrationRule().evaluate(official, world)

    assert [(f.rule_code, f.severity) for f in flags] == [(RuleCode.R06, Severity.LOW)]
    assert "65%" in flags[0].explanation and "81.29" in flags[0].explanation
    assert flags[0].evidence[2].id == COMPANY_ID
    assert flags[0].evidence[1].type is NodeType.ORGAN


def test_r06_silent_when_market_is_balanced(today: date) -> None:
    contracts = [_contract(f"a{i}", make_company(), 5_000_000) for i in range(3)]
    contracts += [_contract(f"b{i}", OTHER, 5_000_000) for i in range(3)]
    world = _world(contracts, today)

    assert SupplierConcentrationRule().evaluate(next(iter(world.officials.values())), world) == []


def test_r06_ignores_codes_outside_authority_scope(today: date) -> None:
    contracts = [_contract(f"a{i}", make_company(), 9_000_000, "42.11.10") for i in range(6)]
    world = _world(contracts, today)

    assert SupplierConcentrationRule().evaluate(next(iter(world.officials.values())), world) == []


def test_r06_needs_enough_contracts(today: date) -> None:
    contracts = [_contract(f"a{i}", make_company(), 9_000_000) for i in range(3)]
    world = _world(contracts, today)

    assert SupplierConcentrationRule().evaluate(next(iter(world.officials.values())), world) == []


def test_r06_ignores_contracts_outside_tenure(today: date) -> None:
    contracts = [
        replace(_contract(f"a{i}", make_company(), 9_000_000), signed_at=date(2019, 1, 1))
        for i in range(6)
    ]
    world = _world(contracts, today)

    assert SupplierConcentrationRule().evaluate(next(iter(world.officials.values())), world) == []
