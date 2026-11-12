from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.modules.appeals.application.dto.appeal_dto import PersonRef
from src.modules.appeals.application.services.appeal_analysis import AppealAnalysisService
from src.modules.appeals.domain.name_matching import matches, parse_mention
from src.modules.appeals.infrastructure.adapters.rule_based_analyzer import RuleBasedAppealAnalyzer


@pytest.mark.parametrize(
    "mention", ["Соколову Андрею Викторовичу", "Соколов А. В.", "А.В. Соколов"]
)
def test_fallback_matches_demo_name(mention: str) -> None:
    query = parse_mention(mention)
    assert query is not None
    assert matches("Соколов Андрей Викторович", query)
    assert not matches("Соколов Пётр Иванович", query)
    if "Андре" in mention:
        assert not matches("Соколов Алексей Викторович", query)
    assert not matches("Соколовский Андрей Викторович", query)


async def test_same_initials_are_ambiguous() -> None:
    directory = AsyncMock()
    directory.find_candidates.return_value = [
        PersonRef(uuid4(), "Иванов Пётр Сергеевич"),
        PersonRef(uuid4(), "Иванов Павел Сергеевич"),
    ]
    analyzer = RuleBasedAppealAnalyzer()
    service = AppealAnalysisService(analyzer, directory)
    analysis = await analyzer.analyze("Иванов П.С. требует взятку.")
    assert await service.link_persons(analysis) == ()
