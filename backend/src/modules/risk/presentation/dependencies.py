from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.dependencies import get_session, get_unit_of_work
from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.modules.risk.application.interfaces.appeals_source import AppealsSourceInterface
from src.modules.risk.application.interfaces.counterparties_source import (
    CounterpartiesSourceInterface,
)
from src.modules.risk.application.interfaces.officials_source import OfficialsSourceInterface
from src.modules.risk.application.interfaces.peer_anomaly_detector import (
    PeerAnomalyDetectorInterface,
)
from src.modules.risk.application.interfaces.risk_repository import RiskRepositoryInterface
from src.modules.risk.application.services.world_loader import RiskWorldLoader
from src.modules.risk.application.use_cases.get_official_flags import GetOfficialFlagsUseCase
from src.modules.risk.application.use_cases.get_official_graph import GetOfficialGraphUseCase
from src.modules.risk.application.use_cases.recompute_risk import RecomputeRiskUseCase
from src.modules.risk.domain.engine import RiskEngine
from src.modules.risk.domain.rules import default_rules
from src.modules.risk.infrastructure.ml.null_detector import NoPeerAnomalyDetector
from src.modules.risk.infrastructure.repositories.risk_repository import RiskRepository

# --- Порты к другим контекстам: реализацию подставляет src/web/create_app.py ---------------


def get_officials_source() -> OfficialsSourceInterface:
    raise NotImplementedError("Overridden in src/web/create_app.py (dependency_overrides)")


def get_counterparties_source() -> CounterpartiesSourceInterface:
    raise NotImplementedError("Overridden in src/web/create_app.py (dependency_overrides)")


def get_appeals_source() -> AppealsSourceInterface:
    raise NotImplementedError("Overridden in src/web/create_app.py (dependency_overrides)")


# --- Модуль ----------------------------------------------------------------------------------


def get_risk_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RiskRepositoryInterface:
    return RiskRepository(session)


def get_peer_anomaly_detector() -> PeerAnomalyDetectorInterface:
    """R08: сюда подключается модель AI-07 (risk/infrastructure/ml/)."""
    return NoPeerAnomalyDetector()


def get_risk_engine() -> RiskEngine:
    return RiskEngine(default_rules())


def get_recompute_risk_use_case(
    officials: Annotated[OfficialsSourceInterface, Depends(get_officials_source)],
    counterparties: Annotated[CounterpartiesSourceInterface, Depends(get_counterparties_source)],
    appeals: Annotated[AppealsSourceInterface, Depends(get_appeals_source)],
    engine: Annotated[RiskEngine, Depends(get_risk_engine)],
    repository: Annotated[RiskRepositoryInterface, Depends(get_risk_repository)],
    unit_of_work: Annotated[UnitOfWorkInterface, Depends(get_unit_of_work)],
    peer_anomalies: Annotated[PeerAnomalyDetectorInterface, Depends(get_peer_anomaly_detector)],
) -> RecomputeRiskUseCase:
    loader = RiskWorldLoader(officials, counterparties, appeals)
    return RecomputeRiskUseCase(loader, engine, repository, unit_of_work, peer_anomalies)


def get_official_flags_use_case(
    repository: Annotated[RiskRepositoryInterface, Depends(get_risk_repository)],
    officials: Annotated[OfficialsSourceInterface, Depends(get_officials_source)],
) -> GetOfficialFlagsUseCase:
    return GetOfficialFlagsUseCase(repository, officials)


def get_official_graph_use_case(
    officials: Annotated[OfficialsSourceInterface, Depends(get_officials_source)],
    counterparties: Annotated[CounterpartiesSourceInterface, Depends(get_counterparties_source)],
    appeals: Annotated[AppealsSourceInterface, Depends(get_appeals_source)],
    repository: Annotated[RiskRepositoryInterface, Depends(get_risk_repository)],
) -> GetOfficialGraphUseCase:
    return GetOfficialGraphUseCase(officials, counterparties, appeals, repository)
