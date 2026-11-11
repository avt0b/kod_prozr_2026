from datetime import date
from uuid import UUID

from src.modules.officials.application.dto.officials_dto import (
    AppointmentDTO,
    AuthorityDTO,
    EmploymentDTO,
    OrganDTO,
    PersonDTO,
    PositionDTO,
    RelativeDTO,
)
from src.modules.officials.domain.appointment import Appointment
from src.modules.officials.domain.organ import Authority, Organ, Position
from src.modules.officials.domain.person import Employment, Kinship, Person


def to_organ_dto(organ: Organ) -> OrganDTO:
    return OrganDTO(id=organ.id, name=organ.name, inn=organ.inn, region=organ.region)


def to_position_dto(position: Position) -> PositionDTO:
    return PositionDTO(
        id=position.id,
        organ_id=position.organ_id,
        title=position.title,
        department=position.department,
        is_corruption_risky=position.is_corruption_risky,
    )


def to_authority_dto(authority: Authority) -> AuthorityDTO:
    return AuthorityDTO(
        id=authority.id,
        position_id=authority.position_id,
        kind=authority.kind.value,
        okpd2=authority.scope.okpd2,
        okved=authority.scope.okved,
        territory=authority.scope.territory,
    )


def to_person_dto(person: Person) -> PersonDTO:
    return PersonDTO(
        id=person.id,
        full_name=person.full_name,
        inn=person.inn,
        birth_date=person.birth_date,
        address=person.address,
        phone=person.phone,
    )


def to_employment_dto(employment: Employment) -> EmploymentDTO:
    return EmploymentDTO(
        id=employment.id,
        person_id=employment.person_id,
        company_id=employment.company_id,
        started_at=employment.period.started_at,
        ended_at=employment.period.ended_at,
    )


def to_appointment_dto(
    appointment: Appointment,
    position: Position,
    organ: Organ,
    authorities: list[Authority],
    today: date,
) -> AppointmentDTO:
    return AppointmentDTO(
        id=appointment.id,
        person_id=appointment.person_id,
        started_at=appointment.period.started_at,
        ended_at=appointment.period.ended_at,
        is_active=appointment.is_active(today),
        position=to_position_dto(position),
        organ=to_organ_dto(organ),
        authorities=tuple(to_authority_dto(a) for a in authorities),
    )


def to_relative_dtos(
    person_id: UUID, kinships: list[Kinship], persons: dict[UUID, Person]
) -> list[RelativeDTO]:
    result: list[RelativeDTO] = []
    for kinship in kinships:
        relation = kinship.relative_of(person_id)
        if relation is None:
            continue
        relative_id, kind = relation
        relative = persons.get(relative_id)
        if relative is None:
            continue
        result.append(
            RelativeDTO(
                person_id=person_id,
                kinship_id=kinship.id,
                kind=kind.value,
                person=to_person_dto(relative),
            )
        )
    return result
