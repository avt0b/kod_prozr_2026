"""AI-07: детектор R08 находит закупщика с аномальными признаками и не трогает обычных."""

from datetime import date, timedelta

from src.modules.risk.domain.facts import (
    AppointmentFacts,
    AuthorityFacts,
    CompanyFacts,
    CompanyRoleFacts,
    ContractFacts,
    OfficialFacts,
    PersonFacts,
)
from src.modules.risk.domain.world import RiskWorld
from src.modules.risk.infrastructure.ml.isolation_forest_detector import (
    IsolationForestPeerDetector,
)
from tests.unit.risk.conftest import ORGAN_ID, TODAY, uid

THRESHOLD = 600_000.0


def build_world() -> RiskWorld:
    officials, companies, contracts, roles = [], [], [], []
    for i in range(14):
        prefix = f"{10 + i}.11"
        officials.append(
            OfficialFacts(
                person=PersonFacts(uid(f"p{i}"), f"Служащий {i}"),
                appointments=(
                    AppointmentFacts(
                        organ_id=ORGAN_ID,
                        organ_name="Орган",
                        position_title="Специалист",
                        started_at=date(2020, 1, 1),
                        authorities=(AuthorityFacts("procurement", (prefix,)),),
                        organ_region="Энская область",
                    ),
                ),
            )
        )
        anomalous = i == 0
        for j in range(12):
            company_id = uid(f"c{i}-{j}")
            signed = date(2024, 1, 10) + timedelta(days=50 * j)
            registered = signed - timedelta(days=40) if anomalous else date(2012, 1, 1)
            companies.append(
                CompanyFacts(
                    company_id, f"ООО {i}-{j}", "7700000000", "active", registered_at=registered
                )  # fmt: skip
            )
            amount = THRESHOLD * 0.95 if anomalous else 150_000 + 13_457.5 * ((i + j) % 7)
            contracts.append(
                ContractFacts(
                    id=uid(f"k{i}-{j}"),
                    reg_number=f"{i}-{j}",
                    customer_organ_id=ORGAN_ID,
                    supplier_company_id=company_id,
                    amount=amount,
                    signed_at=signed,
                    okpd2=f"{prefix}.10.120",
                    method="single_supplier" if anomalous or j % 4 == 0 else "auction",
                )
            )
            roles.append(
                CompanyRoleFacts(company_id, uid(f"dir{i}-{j}"), "director", date(2012, 1, 1))
            )
    return RiskWorld(
        today=TODAY,
        officials=officials,
        companies=companies,
        contracts=contracts,
        company_staff=roles,
    )


def test_detector_flags_only_anomalous_buyer() -> None:
    anomalies = IsolationForestPeerDetector(THRESHOLD).detect(build_world())
    assert [a.person_id for a in anomalies] == [uid("p0")]
    names = {f.name for f in anomalies[0].features}
    assert {"share_near_threshold", "young_supplier_share"} <= names
    assert anomalies[0].severity == "medium"
    assert anomalies[0].peers_count == 13


def test_detector_needs_enough_peers() -> None:
    world = build_world()
    small = RiskWorld(today=TODAY, officials=list(world.officials.values())[:3])
    assert IsolationForestPeerDetector(THRESHOLD).detect(small) == []
