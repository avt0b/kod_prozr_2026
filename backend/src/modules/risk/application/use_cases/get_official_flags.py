from uuid import UUID

from src.modules.risk.application.dto.risk_dto import RiskFlagDTO
from src.modules.risk.application.interfaces.officials_source import OfficialsSourceInterface
from src.modules.risk.application.interfaces.risk_repository import RiskRepositoryInterface
from src.modules.risk.domain.exceptions import RiskSubjectNotFoundError


class GetOfficialFlagsUseCase:
    def __init__(
        self, repository: RiskRepositoryInterface, officials: OfficialsSourceInterface
    ) -> None:
        self._repository = repository
        self._officials = officials

    async def execute(self, person_id: UUID) -> list[RiskFlagDTO]:
        if not await self._officials.officials([person_id]):
            raise RiskSubjectNotFoundError(person_id)
        flags = await self._repository.get_flags([person_id])
        return [RiskFlagDTO.from_entity(f) for f in sorted(flags, key=lambda f: -f.weight)]
