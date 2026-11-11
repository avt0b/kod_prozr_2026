from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from uuid import UUID

from src.modules.risk.domain.facts import (
    AppealMentionFacts,
    CompanyFacts,
    CompanyRoleFacts,
    ContractFacts,
    OfficialFacts,
)


class RiskWorld:
    """Снимок данных, на котором считаются правила. Только чтение, с индексами.

    Правила — чистые функции над RiskWorld, поэтому тестируются без БД.
    """

    def __init__(
        self,
        *,
        today: date,
        officials: Iterable[OfficialFacts] = (),
        companies: Iterable[CompanyFacts] = (),
        company_roles: Iterable[CompanyRoleFacts] = (),
        contracts: Iterable[ContractFacts] = (),
        appeal_mentions: Iterable[AppealMentionFacts] = (),
    ) -> None:
        self.today = today
        self.officials: dict[UUID, OfficialFacts] = {o.person.id: o for o in officials}
        self.companies: dict[UUID, CompanyFacts] = {c.id: c for c in companies}

        self._roles_by_person: dict[UUID, list[CompanyRoleFacts]] = defaultdict(list)
        for role in company_roles:
            self._roles_by_person[role.person_id].append(role)

        self._contracts_by_pair: dict[tuple[UUID, UUID], list[ContractFacts]] = defaultdict(list)
        self._contracts_by_organ: dict[UUID, list[ContractFacts]] = defaultdict(list)
        for contract in contracts:
            pair = (contract.customer_organ_id, contract.supplier_company_id)
            self._contracts_by_pair[pair].append(contract)
            self._contracts_by_organ[contract.customer_organ_id].append(contract)

        self._mentions_by_person: dict[UUID, list[AppealMentionFacts]] = defaultdict(list)
        for mention in appeal_mentions:
            self._mentions_by_person[mention.person_id].append(mention)

    def company(self, company_id: UUID) -> CompanyFacts | None:
        return self.companies.get(company_id)

    def roles_of(self, person_id: UUID) -> list[CompanyRoleFacts]:
        return self._roles_by_person.get(person_id, [])

    def contracts_between(self, organ_id: UUID, company_id: UUID) -> list[ContractFacts]:
        return self._contracts_by_pair.get((organ_id, company_id), [])

    def contracts_of_organ(self, organ_id: UUID) -> list[ContractFacts]:
        return self._contracts_by_organ.get(organ_id, [])

    def mentions_of(self, person_id: UUID) -> list[AppealMentionFacts]:
        return self._mentions_by_person.get(person_id, [])
