from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from src.modules.counterparties.domain.exceptions import InvalidContractAmountError


@dataclass
class Contract:
    """Госконтракт: заказчик — орган (id из officials, без FK), поставщик — компания."""

    reg_number: str
    customer_organ_id: UUID
    supplier_company_id: UUID
    amount: float
    signed_at: date
    okpd2: str | None = None
    method: str | None = None  # способ закупки: auction, single_supplier, ...
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise InvalidContractAmountError()
