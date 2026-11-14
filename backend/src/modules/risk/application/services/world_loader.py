from collections.abc import Sequence
from datetime import date
from uuid import UUID

from src.core.utils.iterables import chunked
from src.modules.risk.application.interfaces.appeals_source import AppealsSourceInterface
from src.modules.risk.application.interfaces.counterparties_source import (
    CounterpartiesSourceInterface,
)
from src.modules.risk.application.interfaces.officials_source import OfficialsSourceInterface
from src.modules.risk.domain.facts import (
    AppealMentionFacts,
    CompanyFacts,
    CompanyRoleFacts,
    ContractFacts,
)
from src.modules.risk.domain.world import RiskWorld

MAX_CONTRACTS = 500_000
MAX_COMPANIES = 100_000


class RiskWorldLoader:
    """Собирает RiskWorld из трёх контекстов через порты. Запросы пачками, без N+1.

    Новое правило требует новых фактов -> добавь их загрузку здесь и поле в RiskWorld.
    """

    def __init__(
        self,
        officials: OfficialsSourceInterface,
        counterparties: CounterpartiesSourceInterface,
        appeals: AppealsSourceInterface,
    ) -> None:
        self._officials = officials
        self._counterparties = counterparties
        self._appeals = appeals

    async def load(
        self, person_ids: Sequence[UUID] | None = None, today: date | None = None
    ) -> RiskWorld:
        ids = list(person_ids) if person_ids is not None else await self._officials.official_ids()
        officials = await self._officials.officials(ids)

        linked_person_ids = list(
            {o.person.id for o in officials} | {r.person.id for o in officials for r in o.relatives}
        )
        roles: list[CompanyRoleFacts] = []
        for batch in chunked(linked_person_ids):
            roles.extend(await self._counterparties.roles_for_persons(batch))

        # Все компании: R05 сверяет контакты поставщиков и отсеивает адреса массовой регистрации.
        companies: list[CompanyFacts] = await self._counterparties.all_companies(MAX_COMPANIES)

        organ_ids = list({a.organ_id for o in officials for a in o.appointments})
        contracts: list[ContractFacts] = []
        for batch in chunked(organ_ids):
            contracts.extend(
                await self._counterparties.contracts(customer_organ_ids=batch, limit=MAX_CONTRACTS)
            )

        # Роли в компаниях-поставщиках: R08 считает долю «номинальных» директоров.
        staff: list[CompanyRoleFacts] = []
        for batch in chunked(list({c.supplier_company_id for c in contracts})):
            staff.extend(await self._counterparties.roles_for_companies(batch))

        mentions: list[AppealMentionFacts] = []
        for batch in chunked([o.person.id for o in officials]):
            mentions.extend(await self._appeals.mentions(batch))

        return RiskWorld(
            today=today or date.today(),
            officials=officials,
            companies=companies,
            company_roles=roles,
            contracts=contracts,
            appeal_mentions=mentions,
            company_staff=staff,
        )
