from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.dependencies import get_audit_log, get_session, get_unit_of_work
from src.core.infrastructure.interfaces.audit_log import AuditLogInterface
from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.modules.officials.application.interfaces.appointment_repository import (
    AppointmentRepositoryInterface,
)
from src.modules.officials.application.interfaces.company_links_source import (
    CompanyLinksSourceInterface,
)
from src.modules.officials.application.interfaces.organ_repository import (
    OrganRepositoryInterface,
)
from src.modules.officials.application.interfaces.person_repository import (
    PersonRepositoryInterface,
)
from src.modules.officials.application.interfaces.risk_source import RiskSourceInterface
from src.modules.officials.application.use_cases.get_official_profile import (
    GetOfficialProfileUseCase,
)
from src.modules.officials.application.use_cases.get_official_snapshots import (
    GetOfficialSnapshotsUseCase,
)
from src.modules.officials.application.use_cases.list_officials import ListOfficialsUseCase
from src.modules.officials.application.use_cases.list_organs import ListOrgansUseCase
from src.modules.officials.infrastructure.repositories.appointment_repository import (
    AppointmentRepository,
)
from src.modules.officials.infrastructure.repositories.organ_repository import OrganRepository
from src.modules.officials.infrastructure.repositories.person_repository import (
    PersonRepository,
)

# --- Порты к другим контекстам: реализацию подставляет src/web/create_app.py ---------------


def get_risk_source() -> RiskSourceInterface:
    raise NotImplementedError("Overridden in src/web/create_app.py (dependency_overrides)")


def get_company_links_source() -> CompanyLinksSourceInterface:
    raise NotImplementedError("Overridden in src/web/create_app.py (dependency_overrides)")


# --- Репозитории и use cases модуля ---------------------------------------------------------


def get_organ_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganRepositoryInterface:
    return OrganRepository(session)


def get_person_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PersonRepositoryInterface:
    return PersonRepository(session)


def get_appointment_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AppointmentRepositoryInterface:
    return AppointmentRepository(session)


def get_official_snapshots_use_case(
    persons: Annotated[PersonRepositoryInterface, Depends(get_person_repository)],
    appointments: Annotated[AppointmentRepositoryInterface, Depends(get_appointment_repository)],
    organs: Annotated[OrganRepositoryInterface, Depends(get_organ_repository)],
) -> GetOfficialSnapshotsUseCase:
    return GetOfficialSnapshotsUseCase(persons, appointments, organs)


def get_list_organs_use_case(
    organs: Annotated[OrganRepositoryInterface, Depends(get_organ_repository)],
) -> ListOrgansUseCase:
    return ListOrgansUseCase(organs)


def get_list_officials_use_case(
    appointments: Annotated[AppointmentRepositoryInterface, Depends(get_appointment_repository)],
    snapshots: Annotated[GetOfficialSnapshotsUseCase, Depends(get_official_snapshots_use_case)],
    risk_source: Annotated[RiskSourceInterface, Depends(get_risk_source)],
) -> ListOfficialsUseCase:
    return ListOfficialsUseCase(appointments, snapshots, risk_source)


def get_official_profile_use_case(
    snapshots: Annotated[GetOfficialSnapshotsUseCase, Depends(get_official_snapshots_use_case)],
    company_links: Annotated[CompanyLinksSourceInterface, Depends(get_company_links_source)],
    risk_source: Annotated[RiskSourceInterface, Depends(get_risk_source)],
    audit: Annotated[AuditLogInterface, Depends(get_audit_log)],
    unit_of_work: Annotated[UnitOfWorkInterface, Depends(get_unit_of_work)],
) -> GetOfficialProfileUseCase:
    return GetOfficialProfileUseCase(snapshots, company_links, risk_source, audit, unit_of_work)
