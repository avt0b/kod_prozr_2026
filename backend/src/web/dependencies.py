"""FastAPI-реализации портов, которые модули объявили заглушками в своих
presentation/dependencies.py. Подключаются в create_app через dependency_overrides."""

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.dependencies import get_session
from src.modules.appeals.presentation import dependencies as appeals_deps
from src.modules.assistant.presentation import dependencies as assistant_deps
from src.modules.manual_graph.presentation.dependencies import get_reference_graph
from src.modules.officials.presentation import dependencies as officials_deps
from src.modules.reports.presentation import dependencies as reports_deps
from src.modules.risk.presentation import dependencies as risk_deps
from src.modules.stats.presentation import dependencies as stats_deps
from src.web import wiring
from src.web.manual_graph_reference import reference_graph


def _on_session[T](builder: Callable[[AsyncSession], T]) -> Callable[..., T]:
    """Обернуть builder(session) в FastAPI-зависимость с сессией запроса."""

    def dependency(session: Annotated[AsyncSession, Depends(get_session)]) -> T:
        return builder(session)

    return dependency


# заглушка модуля -> реализация из composition root
DEPENDENCY_OVERRIDES: dict[Callable[..., Any], Callable[..., Any]] = {
    get_reference_graph: reference_graph,
    assistant_deps.get_assistant_tools: _on_session(wiring.assistant_tools),
    officials_deps.get_risk_source: _on_session(wiring.officials_risk_source),
    officials_deps.get_company_links_source: _on_session(wiring.officials_company_links),
    risk_deps.get_officials_source: _on_session(wiring.risk_officials_source),
    risk_deps.get_counterparties_source: _on_session(wiring.risk_counterparties_source),
    risk_deps.get_appeals_source: _on_session(wiring.risk_appeals_source),
    appeals_deps.get_person_directory: _on_session(wiring.appeals_person_directory),
    reports_deps.get_dossier_source: _on_session(wiring.reports_dossier_source),
    stats_deps.get_officials_counter: _on_session(wiring.stats_officials_counter),
    stats_deps.get_risk_counter: _on_session(wiring.stats_risk_counter),
    stats_deps.get_appeals_counter: _on_session(wiring.stats_appeals_counter),
    stats_deps.get_official_placements: _on_session(wiring.stats_official_placements),
    stats_deps.get_official_risk_profiles: _on_session(wiring.stats_official_risk_profiles),
}
