from collections.abc import Sequence
from datetime import date
from uuid import UUID

from src.modules.risk.application.use_cases.get_official_graph import GetOfficialGraphUseCase
from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import (
    AppealMentionFacts,
    CompanyFacts,
    CompanyRoleFacts,
    ContractFacts,
    OfficialFacts,
    OrganFacts,
    PersonFacts,
    RelativeLinkFacts,
)
from src.modules.risk.domain.flag import EvidenceNode, RiskFlag
from src.modules.risk.domain.graph import contract_group_id
from src.modules.risk.domain.score import RiskScore
from tests.unit.risk.conftest import COMPANY_ID, ORGAN_ID, make_official, uid

OFFICIAL = make_official(with_spouse=False)
MOTHER = PersonFacts(uid("mother"), "Белова Галина Петровна")


class _Officials:
    async def official_ids(self) -> list[UUID]:
        return [OFFICIAL.person.id]

    async def officials(self, person_ids: Sequence[UUID]) -> list[OfficialFacts]:
        return [OFFICIAL] if OFFICIAL.person.id in person_ids else []

    async def persons(self, person_ids: Sequence[UUID]) -> list[PersonFacts]:
        return []

    async def relatives(self, person_ids: Sequence[UUID]) -> list[RelativeLinkFacts]:
        if OFFICIAL.person.id in person_ids:
            return [RelativeLinkFacts(OFFICIAL.person.id, MOTHER, "parent")]
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
        return [ContractFacts(uid("c1"), "1", ORGAN_ID, COMPANY_ID, 1_000_000, date(2024, 4, 1))]


class _Appeals:
    async def mentions(self, person_ids: Sequence[UUID]) -> list[AppealMentionFacts]:
        return []


class _Repository:
    async def get_flags(self, person_ids: Sequence[UUID]) -> list[RiskFlag]:
        evidence = (
            EvidenceNode(NodeType.PERSON, OFFICIAL.person.id, "Иванов П.С."),
            EvidenceNode(NodeType.PERSON, MOTHER.id, "Белова Г.П."),
            EvidenceNode(NodeType.COMPANY, COMPANY_ID, "ООО «Чистый Двор»"),
            EvidenceNode(NodeType.ORGAN, ORGAN_ID, "Администрация"),
        )
        return [
            RiskFlag(OFFICIAL.person.id, RuleCode.R05, "shared_contacts", Severity.MEDIUM, 20,
                     "тест", evidence)
        ]  # fmt: skip

    async def get_scores(self, person_ids: Sequence[UUID]) -> list[RiskScore]:
        return []


async def test_graph_contains_r05_chain_with_shared_contact_edge() -> None:
    use_case = GetOfficialGraphUseCase(
        _Officials(),
        _Counterparties(),
        _Appeals(),
        _Repository(),  # type: ignore[arg-type]
    )

    graph = await use_case.execute(OFFICIAL.person.id, depth=1)

    node_ids = {n.id for n in graph.nodes}
    assert {OFFICIAL.person.id, MOTHER.id, COMPANY_ID, ORGAN_ID} <= node_ids
    edges = {(e.source, e.target, e.type) for e in graph.edges}
    assert (MOTHER.id, COMPANY_ID, "shared_contact") in edges
    assert (OFFICIAL.person.id, ORGAN_ID, "works_in") in edges
    assert (
        contract_group_id(COMPANY_ID, ORGAN_ID) in node_ids
    )  # контракт компании с органом дотянулся до цепочки
