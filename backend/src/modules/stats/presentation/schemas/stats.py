from datetime import datetime

from src.core.schemas import APIModel


class OverviewResponse(APIModel):
    officials_total: int
    officials_with_flags: int
    flags_by_severity: dict[str, int]  # {"high": n, "medium": n, "low": n}
    appeals_total: int
    appeals_by_status: dict[str, int]  # {"new": n, "analyzed": n, "routed": n, "closed": n}
    computed_at: datetime | None  # последний пересчёт риска
