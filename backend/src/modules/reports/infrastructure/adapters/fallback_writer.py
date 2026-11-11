from src.core.exceptions import ExternalServiceError
from src.core.infrastructure.logger import get_logger
from src.modules.reports.application.interfaces.report_writer import (
    ReportWriterInterface,
    WrittenReport,
)
from src.modules.reports.domain.dossier import Dossier

logger = get_logger(__name__)


class FallbackReportWriter:
    def __init__(self, primary: ReportWriterInterface, fallback: ReportWriterInterface) -> None:
        self._primary = primary
        self._fallback = fallback

    async def write(self, dossier: Dossier) -> WrittenReport:
        try:
            written = await self._primary.write(dossier)
            if written.text.strip():
                return written
        except ExternalServiceError as exc:
            logger.warning("Primary report writer failed ({}), using template", exc.message)
        return await self._fallback.write(dossier)
