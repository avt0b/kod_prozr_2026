from src.core.schemas import APIModel


class OverviewResponse(APIModel):
    officials_total: int
    officials_flagged: int
    flags_by_severity: dict[str, int]  # {"low": n, "medium": n, "high": n}
    appeals_by_status: dict[str, int]  # {"new": n, "analyzed": n, "routed": n, "closed": n}
