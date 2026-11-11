from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID

from src.modules.risk.domain.flag import RiskFlag
from src.modules.risk.domain.rules.base import RiskRule
from src.modules.risk.domain.score import RiskScore, ScorePolicy
from src.modules.risk.domain.world import RiskWorld


@dataclass(frozen=True)
class RiskAssessment:
    flags: list[RiskFlag]
    scores: list[RiskScore]
    computed_at: datetime


class RiskEngine:
    """Доменный сервис: прогоняет правила по всем служащим мира и считает баллы."""

    def __init__(self, rules: list[RiskRule], policy: ScorePolicy | None = None) -> None:
        self._rules = rules
        self._policy = policy or ScorePolicy()

    def assess(
        self,
        world: RiskWorld,
        computed_at: datetime | None = None,
        carried_flags: Sequence[RiskFlag] = (),
    ) -> RiskAssessment:
        """carried_flags — флаги прошлого расчёта, которые нельзя пересчитать на этом снимке
        (R08 при частичном пересчёте): они входят в балл как есть."""
        computed_at = computed_at or datetime.now(UTC)
        carried: dict[UUID, list[RiskFlag]] = defaultdict(list)
        for flag in carried_flags:
            carried[flag.person_id].append(flag)
        all_flags: list[RiskFlag] = []
        scores: list[RiskScore] = []
        for official in world.officials.values():
            flags = [
                replace(flag, computed_at=computed_at)
                for rule in self._rules
                for flag in rule.evaluate(official, world)
            ]
            flags += [replace(f, computed_at=computed_at) for f in carried[official.person.id]]
            all_flags.extend(flags)
            scores.append(self._policy.score(official.person.id, flags, computed_at))
        return RiskAssessment(flags=all_flags, scores=scores, computed_at=computed_at)
