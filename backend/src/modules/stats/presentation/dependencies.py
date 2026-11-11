from typing import Annotated

from fastapi import Depends

from src.modules.stats.application.interfaces.sources import (
    AppealsCounterInterface,
    OfficialsCounterInterface,
    RiskCounterInterface,
)
from src.modules.stats.application.use_cases.get_overview import GetOverviewUseCase


def get_officials_counter() -> OfficialsCounterInterface:
    raise NotImplementedError("Overridden in src/web/create_app.py (dependency_overrides)")


def get_risk_counter() -> RiskCounterInterface:
    raise NotImplementedError("Overridden in src/web/create_app.py (dependency_overrides)")


def get_appeals_counter() -> AppealsCounterInterface:
    raise NotImplementedError("Overridden in src/web/create_app.py (dependency_overrides)")


def get_overview_use_case(
    officials: Annotated[OfficialsCounterInterface, Depends(get_officials_counter)],
    risk: Annotated[RiskCounterInterface, Depends(get_risk_counter)],
    appeals: Annotated[AppealsCounterInterface, Depends(get_appeals_counter)],
) -> GetOverviewUseCase:
    return GetOverviewUseCase(officials, risk, appeals)
