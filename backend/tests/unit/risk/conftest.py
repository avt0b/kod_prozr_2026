"""Мини-мир для правил риска: служащий-закупщик, его супруга и компания супруги."""

from datetime import date
from uuid import UUID, uuid5

import pytest

from src.modules.risk.domain.facts import (
    AppointmentFacts,
    AuthorityFacts,
    CompanyFacts,
    CompanyRoleFacts,
    ContractFacts,
    OfficialFacts,
    PersonFacts,
    RelativeFacts,
)

NS = UUID("00000000-0000-0000-0000-00000000abcd")
TODAY = date(2026, 11, 11)


def uid(key: str) -> UUID:
    return uuid5(NS, key)


ORGAN_ID = uid("organ")
OTHER_ORGAN_ID = uid("other-organ")
COMPANY_ID = uid("company")


def make_official(
    *,
    authorities: tuple[AuthorityFacts, ...] = (AuthorityFacts("procurement", ("41.20",)),),
    started_at: date = date(2021, 3, 1),
    with_spouse: bool = True,
) -> OfficialFacts:
    spouse = PersonFacts(uid("spouse"), "Иванова Анна Викторовна")
    return OfficialFacts(
        person=PersonFacts(uid("official"), "Иванов Пётр Сергеевич"),
        appointments=(
            AppointmentFacts(
                organ_id=ORGAN_ID,
                organ_name="Администрация города Энска",
                position_title="Начальник отдела закупок",
                started_at=started_at,
                authorities=authorities,
            ),
        ),
        relatives=(RelativeFacts(spouse, "spouse"),) if with_spouse else (),
    )


def make_company(status: str = "active") -> CompanyFacts:
    return CompanyFacts(id=COMPANY_ID, name="ООО «СтройРесурс»", inn="7702000011", status=status)


def make_role(person_key: str, role: str = "founder") -> CompanyRoleFacts:
    return CompanyRoleFacts(
        company_id=COMPANY_ID,
        person_id=uid(person_key),
        role=role,
        started_at=date(2018, 5, 14),
        share=100.0 if role == "founder" else None,
    )


def make_contract(
    key: str,
    signed_at: date,
    *,
    organ_id: UUID = ORGAN_ID,
    okpd2: str = "41.20.40",
    amount: float = 8_400_000,
) -> ContractFacts:
    return ContractFacts(
        id=uid(key),
        reg_number=f"37701{key}",
        customer_organ_id=organ_id,
        supplier_company_id=COMPANY_ID,
        amount=amount,
        signed_at=signed_at,
        okpd2=okpd2,
    )


@pytest.fixture
def today() -> date:
    return TODAY
