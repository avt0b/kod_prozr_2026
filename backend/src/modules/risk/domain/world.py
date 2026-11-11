from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from uuid import UUID

from src.modules.risk.domain.contacts import normalize_address, normalize_phone
from src.modules.risk.domain.facts import (
    AppealMentionFacts,
    CompanyFacts,
    CompanyRoleFacts,
    ContractFacts,
    OfficialFacts,
    PeerAnomalyFacts,
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

        # Сколько компаний на одном адресе / телефоне: адреса массовой регистрации (R05).
        self._companies_per_address: dict[str, int] = defaultdict(int)
        self._companies_per_phone: dict[str, int] = defaultdict(int)
        for company in self.companies.values():
            if address := normalize_address(company.address):
                self._companies_per_address[address] += 1
            if phone := normalize_phone(company.phone):
                self._companies_per_phone[phone] += 1

        self._peer_anomalies: dict[UUID, PeerAnomalyFacts] = {}
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

    def attach_peer_anomalies(self, anomalies: Iterable[PeerAnomalyFacts]) -> None:
        """Результаты ML-детектора R08: считаются по всему снимку уже после его сборки."""
        self._peer_anomalies = {a.person_id: a for a in anomalies}

    def peer_anomaly_of(self, person_id: UUID) -> PeerAnomalyFacts | None:
        return self._peer_anomalies.get(person_id)

    def companies_at_address(self, normalized_address: str) -> int:
        return self._companies_per_address.get(normalized_address, 0)

    def companies_with_phone(self, normalized_phone: str) -> int:
        return self._companies_per_phone.get(normalized_phone, 0)

    def mentions_of(self, person_id: UUID) -> list[AppealMentionFacts]:
        return self._mentions_by_person.get(person_id, [])
