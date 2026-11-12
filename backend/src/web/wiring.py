"""Сборка межмодульных связок на сессии БД — без FastAPI.

Это composition root (как src/web/dependencies.py в optimus): только здесь известны все
модули сразу. Published language каждого модуля (Query*UseCase) оборачивается
ACL-адаптером модуля-потребителя. Используется и HTTP-зависимостями (dependencies.py),
и подписчиками событий (event_handlers.py), и сидами (src/seed).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from src.core.infrastructure.repositories.audit_log_repository import AuditLogRepository
from src.modules.appeals.application.use_cases.query_appeals import QueryAppealsUseCase
from src.modules.appeals.infrastructure.adapters.officials_acl import (
    OfficialsDirectoryACLAdapter,
)
from src.modules.appeals.infrastructure.repositories.appeal_repository import AppealRepository
from src.modules.counterparties.application.use_cases.query_counterparties import (
    QueryCounterpartiesUseCase,
)
from src.modules.counterparties.infrastructure.repositories.company_repository import (
    CompanyRepository,
)
from src.modules.counterparties.infrastructure.repositories.contract_repository import (
    ContractRepository,
)
from src.modules.officials.application.use_cases.query_officials import QueryOfficialsUseCase
from src.modules.officials.infrastructure.adapters.counterparties_acl import (
    CounterpartiesACLAdapter as OfficialsCounterpartiesACL,
)
from src.modules.officials.infrastructure.adapters.risk_acl import RiskACLAdapter
from src.modules.officials.infrastructure.repositories.appointment_repository import (
    AppointmentRepository,
)
from src.modules.officials.infrastructure.repositories.organ_repository import OrganRepository
from src.modules.officials.infrastructure.repositories.person_repository import (
    PersonRepository,
)
from src.modules.reports.infrastructure.adapters.dossier_acl import DossierACLAdapter
from src.modules.risk.application.services.world_loader import RiskWorldLoader
from src.modules.risk.application.use_cases.query_risk import QueryRiskUseCase
from src.modules.risk.application.use_cases.recompute_risk import RecomputeRiskUseCase
from src.modules.risk.domain.engine import RiskEngine
from src.modules.risk.domain.rules import default_rules
from src.modules.risk.infrastructure.adapters.appeals_acl import AppealsACLAdapter
from src.modules.risk.infrastructure.adapters.counterparties_acl import (
    CounterpartiesACLAdapter as RiskCounterpartiesACL,
)
from src.modules.risk.infrastructure.adapters.officials_acl import OfficialsACLAdapter
from src.modules.risk.infrastructure.repositories.risk_repository import RiskRepository
from src.modules.risk.presentation.dependencies import get_peer_anomaly_detector
from src.modules.stats.infrastructure.adapters.acl import (
    AppealsCounterACLAdapter,
    OfficialsCounterACLAdapter,
    RiskCounterACLAdapter,
)

# --- Published language модулей --------------------------------------------------------------


def officials_query(session: AsyncSession) -> QueryOfficialsUseCase:
    return QueryOfficialsUseCase(
        PersonRepository(session), AppointmentRepository(session), OrganRepository(session)
    )


def counterparties_query(session: AsyncSession) -> QueryCounterpartiesUseCase:
    return QueryCounterpartiesUseCase(CompanyRepository(session), ContractRepository(session))


def risk_query(session: AsyncSession) -> QueryRiskUseCase:
    return QueryRiskUseCase(RiskRepository(session))


def appeals_query(session: AsyncSession) -> QueryAppealsUseCase:
    return QueryAppealsUseCase(AppealRepository(session))


# --- officials <- risk, counterparties --------------------------------------------------------


def officials_risk_source(session: AsyncSession) -> RiskACLAdapter:
    return RiskACLAdapter(risk_query(session))


def officials_company_links(session: AsyncSession) -> OfficialsCounterpartiesACL:
    return OfficialsCounterpartiesACL(counterparties_query(session))


# --- risk <- officials, counterparties, appeals ----------------------------------------------


def risk_officials_source(session: AsyncSession) -> OfficialsACLAdapter:
    return OfficialsACLAdapter(officials_query(session))


def risk_counterparties_source(session: AsyncSession) -> RiskCounterpartiesACL:
    return RiskCounterpartiesACL(counterparties_query(session))


def risk_appeals_source(session: AsyncSession) -> AppealsACLAdapter:
    return AppealsACLAdapter(appeals_query(session))


def recompute_risk_use_case(session: AsyncSession) -> RecomputeRiskUseCase:
    loader = RiskWorldLoader(
        risk_officials_source(session),
        risk_counterparties_source(session),
        risk_appeals_source(session),
    )
    return RecomputeRiskUseCase(
        loader,
        RiskEngine(default_rules()),
        RiskRepository(session),
        SqlAlchemyUnitOfWork(session),
        get_peer_anomaly_detector(),
        AuditLogRepository(session),
    )


# --- appeals, reports, stats <- ... -----------------------------------------------------------


def appeals_person_directory(session: AsyncSession) -> OfficialsDirectoryACLAdapter:
    return OfficialsDirectoryACLAdapter(officials_query(session), risk_query(session))


def reports_dossier_source(session: AsyncSession) -> DossierACLAdapter:
    return DossierACLAdapter(officials_query(session), risk_query(session), appeals_query(session))


def stats_officials_counter(session: AsyncSession) -> OfficialsCounterACLAdapter:
    return OfficialsCounterACLAdapter(officials_query(session))


def stats_risk_counter(session: AsyncSession) -> RiskCounterACLAdapter:
    return RiskCounterACLAdapter(risk_query(session))


def stats_appeals_counter(session: AsyncSession) -> AppealsCounterACLAdapter:
    return AppealsCounterACLAdapter(appeals_query(session))
