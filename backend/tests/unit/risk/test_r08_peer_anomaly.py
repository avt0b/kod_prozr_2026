from collections.abc import Sequence
from datetime import UTC, date, datetime
from uuid import UUID

from src.modules.risk.application.services.world_loader import RiskWorldLoader
from src.modules.risk.application.use_cases.recompute_risk import RecomputeRiskUseCase
from src.modules.risk.domain.engine import RiskEngine
from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import (
    AppealMentionFacts,
    CompanyFacts,
    CompanyRoleFacts,
    ContractFacts,
    FeatureDeviation,
    OfficialFacts,
    OrganFacts,
    PeerAnomalyFacts,
    PersonFacts,
    RelativeLinkFacts,
)
from src.modules.risk.domain.flag import EvidenceNode, RiskFlag
from src.modules.risk.domain.rules import default_rules
from src.modules.risk.domain.rules.r08_peer_anomaly import PeerAnomalyRule
from src.modules.risk.domain.score import RiskScore
from src.modules.risk.domain.world import RiskWorld
from tests.unit.risk.conftest import make_official

OFFICIAL = make_official(with_spouse=False)
FEATURES = (
    FeatureDeviation("share_near_threshold", "доля закупок чуть ниже порога", 0.4, 0.08, 4.1),
    FeatureDeviation("young_supplier_share", "доля молодых поставщиков", 0.5, 0.1, 3.2),
    FeatureDeviation("contracts_per_year", "контрактов в год", 31, 12, 1.1),
    FeatureDeviation("share_round_amounts", "доля круглых сумм", 0.2, 0.15, 0.4),
)
ANOMALY = PeerAnomalyFacts(OFFICIAL.person.id, "medium", 14, FEATURES)


def test_r08_turns_detector_result_into_explained_flag(today: date) -> None:
    world = RiskWorld(today=today, officials=[OFFICIAL])
    world.attach_peer_anomalies([ANOMALY])

    flags = PeerAnomalyRule().evaluate(OFFICIAL, world)

    assert [(f.rule_code, f.severity, f.weight) for f in flags] == [
        (RuleCode.R08, Severity.MEDIUM, 5)
    ]
    text = flags[0].explanation
    assert "14 чел." in text and "40% при медиане коллег 8%" in text
    assert "доля круглых сумм" not in text  # только 3 признака с наибольшим |z|
    assert [n.type for n in flags[0].evidence] == [NodeType.PERSON, NodeType.ORGAN]


def test_r08_silent_without_detector_result(today: date) -> None:
    world = RiskWorld(today=today, officials=[OFFICIAL])

    assert PeerAnomalyRule().evaluate(OFFICIAL, world) == []


# --- пересчёт: детектор только при полном, перенос R08 при частичном -------------------------


class _Officials:
    async def official_ids(self) -> list[UUID]:
        return [OFFICIAL.person.id]

    async def officials(self, person_ids: Sequence[UUID]) -> list[OfficialFacts]:
        return [OFFICIAL]

    async def persons(self, person_ids: Sequence[UUID]) -> list[PersonFacts]:
        return []

    async def relatives(self, person_ids: Sequence[UUID]) -> list[RelativeLinkFacts]:
        return []

    async def organs(self, organ_ids: Sequence[UUID]) -> list[OrganFacts]:
        return []


class _Counterparties:
    async def roles_for_persons(self, person_ids: Sequence[UUID]) -> list[CompanyRoleFacts]:
        return []

    async def roles_for_companies(self, company_ids: Sequence[UUID]) -> list[CompanyRoleFacts]:
        return []

    async def companies(self, company_ids: Sequence[UUID]) -> list[CompanyFacts]:
        return []

    async def all_companies(self, limit: int) -> list[CompanyFacts]:
        return []

    async def contracts(
        self,
        *,
        customer_organ_ids: Sequence[UUID] | None = None,
        supplier_company_ids: Sequence[UUID] | None = None,
        limit: int,
    ) -> list[ContractFacts]:
        return []


class _Appeals:
    async def mentions(self, person_ids: Sequence[UUID]) -> list[AppealMentionFacts]:
        return []


class _Repository:
    def __init__(self, stored: list[RiskFlag]) -> None:
        self.stored = stored
        self.saved: list[RiskFlag] = []

    async def replace_all(self, flags: list[RiskFlag], scores: list[RiskScore]) -> None:
        self.saved = flags

    async def replace_for_persons(
        self, person_ids: Sequence[UUID], flags: list[RiskFlag], scores: list[RiskScore]
    ) -> None:
        self.saved = flags

    async def get_flags(self, person_ids: Sequence[UUID]) -> list[RiskFlag]:
        return self.stored


class _UnitOfWork:
    async def __aenter__(self) -> "_UnitOfWork":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _Detector:
    def __init__(self) -> None:
        self.calls = 0

    def detect(self, world: RiskWorld) -> list[PeerAnomalyFacts]:
        self.calls += 1
        return [ANOMALY]


def _use_case(repository: _Repository, detector: _Detector) -> RecomputeRiskUseCase:
    loader = RiskWorldLoader(_Officials(), _Counterparties(), _Appeals())
    return RecomputeRiskUseCase(
        loader,
        RiskEngine(default_rules()),
        repository,  # type: ignore[arg-type]
        _UnitOfWork(),
        detector,
    )


async def test_full_recompute_runs_detector() -> None:
    repository, detector = _Repository([]), _Detector()

    await _use_case(repository, detector).execute()

    assert detector.calls == 1
    assert [f.rule_code for f in repository.saved] == [RuleCode.R08]


async def test_partial_recompute_carries_previous_r08_without_detector() -> None:
    previous = RiskFlag(
        OFFICIAL.person.id,
        RuleCode.R08,
        "peer_anomaly",
        Severity.LOW,
        5,
        "аномалия",
        (EvidenceNode(NodeType.PERSON, OFFICIAL.person.id, "Иванов П.С."),),
        computed_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    repository, detector = _Repository([previous]), _Detector()

    await _use_case(repository, detector).execute([OFFICIAL.person.id])

    assert detector.calls == 0
    assert [(f.rule_code, f.explanation) for f in repository.saved] == [(RuleCode.R08, "аномалия")]
