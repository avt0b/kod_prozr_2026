from dataclasses import dataclass
from uuid import UUID

from src.core.utils.text import short_name
from src.modules.risk.domain.contacts import normalize_address, normalize_phone
from src.modules.risk.domain.enums import RuleCode, Severity
from src.modules.risk.domain.facts import (
    AppointmentFacts,
    CompanyFacts,
    ContractFacts,
    OfficialFacts,
    PersonFacts,
)
from src.modules.risk.domain.flag import RiskFlag
from src.modules.risk.domain.rules.base import (
    RiskRule,
    company_node,
    contract_nodes,
    contracts_summary,
    organ_node,
    person_node,
    quoted,
)
from src.modules.risk.domain.world import RiskWorld

# Адрес или телефон, на котором зарегистрировано больше компаний, считаем адресом массовой
# регистрации (бизнес-центр, юрадрес) и совпадение с ним не флагуем (data.md §5).
MASS_REGISTRATION_THRESHOLD = 5


@dataclass(frozen=True)
class _Match:
    person: PersonFacts
    kinship_label: str | None
    company: CompanyFacts
    field: str  # «адрес» | «телефон»
    appointment: AppointmentFacts
    contracts: tuple[ContractFacts, ...]


class SharedContactsRule(RiskRule):
    """R05. У компании-подрядчика органа тот же адрес или телефон, что у служащего или его
    родственника.

    Подрядчик — компания с контрактами органа, подписанными в период назначения служащего.
    Адреса и телефоны сравниваются после нормализации (domain/contacts.py). Адреса и телефоны
    массовой регистрации (> MASS_REGISTRATION_THRESHOLD компаний) не учитываются.
    Один флаг на пару (человек, компания).
    """

    code = RuleCode.R05
    name = "shared_contacts"
    severity = Severity.MEDIUM
    legal_ref = "273-ФЗ ст. 10"

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        suppliers = self._suppliers(official, world)
        if not suppliers:
            return []
        people: list[tuple[PersonFacts, str | None]] = [(official.person, None)]
        people += [(r.person, r.kind_label) for r in official.relatives]

        matches: dict[tuple[UUID, UUID], _Match] = {}
        for person, kinship_label in people:
            address = normalize_address(person.address)
            phone = normalize_phone(person.phone)
            for company, appointment, contracts in suppliers.values():
                key = (person.id, company.id)
                if key in matches:
                    continue
                field = None
                if phone and phone == normalize_phone(company.phone):
                    if world.companies_with_phone(phone) <= MASS_REGISTRATION_THRESHOLD:
                        field = "телефон"
                if field is None and address and address == normalize_address(company.address):
                    if world.companies_at_address(address) <= MASS_REGISTRATION_THRESHOLD:
                        field = "адрес"
                if field is not None:
                    matches[key] = _Match(
                        person, kinship_label, company, field, appointment, tuple(contracts)
                    )
        return [self._flag(official, m) for m in matches.values()]

    @staticmethod
    def _suppliers(
        official: OfficialFacts, world: RiskWorld
    ) -> dict[UUID, tuple[CompanyFacts, AppointmentFacts, list[ContractFacts]]]:
        found: dict[UUID, tuple[CompanyFacts, AppointmentFacts, list[ContractFacts]]] = {}
        for appointment in official.appointments:
            for contract in world.contracts_of_organ(appointment.organ_id):
                if not appointment.contains(contract.signed_at):
                    continue
                company = world.company(contract.supplier_company_id)
                if company is None:
                    continue
                entry = found.setdefault(company.id, (company, appointment, []))
                entry[2].append(contract)
        return found

    def _flag(self, official: OfficialFacts, match: _Match) -> RiskFlag:
        official_name = short_name(official.person.full_name)
        if match.kinship_label is None:
            whose = f"служащего {official_name}"
        else:
            whose = (
                f"{short_name(match.person.full_name)} ({match.kinship_label} служащего: "
                f"{official_name})"
            )
        explanation = (
            f"{match.field.capitalize()} подрядчика {quoted(match.company.name)} "
            f"(ИНН {match.company.inn}) совпадает с {_genitive(match.field)} {whose}. "
            f"Компания получила от «{match.appointment.organ_name}» "
            f"{contracts_summary(match.contracts)} в период, когда {official_name} замещал(а) "
            f"должность «{match.appointment.position_title}». Это может свидетельствовать о "
            "скрытой аффилированности с подрядчиком."
        )
        evidence = [person_node(official.person)]
        if match.kinship_label is not None:
            evidence.append(person_node(match.person))
        evidence += [
            company_node(match.company),
            *contract_nodes(match.contracts),
            organ_node(match.appointment.organ_id, match.appointment.organ_name),
        ]
        return self.make_flag(official, explanation, evidence)


def _genitive(field: str) -> str:
    return {"адрес": "адресом", "телефон": "телефоном"}[field]
