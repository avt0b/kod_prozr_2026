"""R08: аномалии закупок служащего относительно коллег (AI-07, docs/ai.md §4).

Сравниваются служащие с полномочием `procurement` и кодами ОКПД2: только у них есть
«свои» закупки. Признаки считаются по контрактам органа в сфере полномочия за период
назначения, стандартизируются робастно (медиана и MAD) внутри группы коллег (та же должность
и регион, не меньше 8 человек, иначе — все закупщики региона), затем IsolationForest ищет выбросы.

Флаг получает служащий, которого модель относит к выбросам и у которого хотя бы один
признак отклоняется от коллег в «рискованную» сторону сильнее MIN_Z. Severity — medium,
если таких признаков два и больше с |z| > 2.5. Признаки, дублирующие правила (доля
крупнейшего поставщика — R06, связанные компании — R01/R02), в модель не входят.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from statistics import median

import numpy as np
from sklearn.ensemble import IsolationForest

from src.core.infrastructure.logger import get_logger
from src.modules.risk.application.interfaces.peer_anomaly_detector import (
    PeerAnomalyDetectorInterface,
)
from src.modules.risk.domain.facts import (
    PROCUREMENT,
    AppointmentFacts,
    ContractFacts,
    FeatureDeviation,
    OfficialFacts,
    PeerAnomalyFacts,
)
from src.modules.risk.domain.world import RiskWorld

logger = get_logger(__name__)

DEFAULT_THRESHOLD = 600_000.0  # тот же параметр, что --threshold генератора (data.md §3)
NEAR_THRESHOLD_FROM = 0.9
YOUNG_SUPPLIER_DAYS = 183
NOMINEE_DIRECTORSHIPS = 5
ROUND_STEP = 100_000
MIN_CONTRACTS = 5
MIN_PEERS = 8
TARGET_SHARE = 0.05  # верхние 5 % служащих (ai.md §4)
MIN_Z = 2.0
MAD_TO_STD = 1.4826
MEDIUM_Z = 2.5

FEATURES: tuple[tuple[str, str, float], ...] = (
    # имя, подпись, минимальное стандартное отклонение (доли и интенсивность)
    ("share_single_supplier", "доля закупок у единственного поставщика", 0.05),
    ("share_near_threshold", "доля закупок чуть ниже порога", 0.05),
    ("share_round_amounts", "доля «круглых» сумм", 0.05),
    ("young_supplier_share", "доля поставщиков, зарегистрированных за полгода до контракта", 0.05),
    ("nominee_director_share", "доля поставщиков с директором пяти и более компаний", 0.05),
    ("contracts_per_year", "закупок в год", 1.0),
)


# Интенсивность закупок помогает модели, но сама по себе флаг не даёт: большой объём сферы
# полномочий — не признак риска.
CONTEXT_ONLY = frozenset({len(FEATURES) - 1})


@dataclass(frozen=True)
class _Profile:
    official: OfficialFacts
    group: tuple[str, str]
    values: tuple[float, ...]


class IsolationForestPeerDetector(PeerAnomalyDetectorInterface):
    def __init__(self, threshold: float = DEFAULT_THRESHOLD, random_state: int = 42) -> None:
        self._threshold = threshold
        self._random_state = random_state

    def detect(self, world: RiskWorld) -> list[PeerAnomalyFacts]:
        profiles = [p for o in world.officials.values() if (p := self._profile(o, world))]
        if len(profiles) < MIN_PEERS:
            return []
        groups = self._groups(profiles)
        z_rows: list[list[float]] = []
        stats: list[tuple[list[float], list[float]]] = []  # (медианы, z) на служащего
        for profile in profiles:
            peers = groups[profile.group]
            z, medians = [], []
            for index, (_, _, min_std) in enumerate(FEATURES):
                column = [p.values[index] for p in peers]
                center = median(column)
                # Робастный z: медиана и MAD, чтобы сами выбросы не раздували разброс группы.
                mad = median(abs(v - center) for v in column) * MAD_TO_STD
                z.append((profile.values[index] - center) / max(min_std, mad))
                medians.append(center)
            z_rows.append(z)
            stats.append((medians, z))
        contamination = min(0.5, max(0.01, TARGET_SHARE * len(world.officials) / len(profiles)))
        model = IsolationForest(
            n_estimators=200, contamination=contamination, random_state=self._random_state
        )
        labels = model.fit_predict(np.array(z_rows))
        result: list[PeerAnomalyFacts] = []
        for profile, label, (medians, z) in zip(profiles, labels, stats, strict=True):
            risky = [i for i, value in enumerate(z) if value >= MIN_Z and i not in CONTEXT_ONLY]
            if label != -1 or not risky:
                continue
            strong = sum(1 for i in risky if z[i] > MEDIUM_Z)
            result.append(
                PeerAnomalyFacts(
                    person_id=profile.official.person.id,
                    severity="medium" if strong >= 2 else "low",
                    peers_count=len(groups[profile.group]) - 1,
                    features=tuple(
                        FeatureDeviation(
                            name=FEATURES[i][0],
                            label=FEATURES[i][1],
                            value=round(profile.values[i], 3),
                            peer_median=round(medians[i], 3),
                            z=round(z[i], 2),
                        )
                        for i in risky
                    ),
                )
            )
        logger.info(
            "R08: {} comparable officials, contamination {:.2f}, {} anomalies",
            len(profiles),
            contamination,
            len(result),
        )
        return result

    def _profile(self, official: OfficialFacts, world: RiskWorld) -> _Profile | None:
        scoped = [
            a for a in official.appointments if any(x.okpd2 for x in a.authorities_of(PROCUREMENT))
        ]
        if not scoped:
            return None
        contracts: dict[object, ContractFacts] = {}
        days = 0
        for appointment in scoped:
            prefixes = tuple(p for x in appointment.authorities_of(PROCUREMENT) for p in x.okpd2)
            for contract in world.contracts_of_organ(appointment.organ_id):
                if (
                    contract.okpd2
                    and contract.okpd2.startswith(prefixes)
                    and appointment.contains(contract.signed_at)
                ):
                    contracts[contract.id] = contract
            days += _active_days(appointment, world, list(contracts.values()))
        items = list(contracts.values())
        if len(items) < MIN_CONTRACTS:
            return None
        values = (
            _share(items, lambda c: c.method == "single_supplier"),
            _share(
                items,
                lambda c: NEAR_THRESHOLD_FROM * self._threshold <= c.amount < self._threshold,
            ),
            _share(items, lambda c: c.amount >= ROUND_STEP and c.amount % ROUND_STEP == 0),
            _share(items, lambda c: _young(c, world)),
            _share(items, lambda c: _nominee(c, world)),
            len(items) / max(days / 365.25, 0.25),
        )
        latest = max(scoped, key=lambda a: a.started_at)
        return _Profile(official, _group_key(latest), values)

    @staticmethod
    def _groups(profiles: list[_Profile]) -> dict[tuple[str, str], list[_Profile]]:
        by_title: dict[tuple[str, str], list[_Profile]] = defaultdict(list)
        for profile in profiles:
            by_title[profile.group].append(profile)
        by_region: dict[str, list[_Profile]] = defaultdict(list)
        for profile in profiles:
            by_region[profile.group[1]].append(profile)
        return {
            key: members if len(members) >= MIN_PEERS else by_region[key[1]]
            for key, members in by_title.items()
        }


def _group_key(appointment: AppointmentFacts) -> tuple[str, str]:
    title = " ".join(appointment.position_title.lower().replace("ё", "е").split())
    return title, appointment.organ_region or ""


def _active_days(
    appointment: AppointmentFacts, world: RiskWorld, contracts: list[ContractFacts]
) -> int:
    """Длительность назначения в пределах периода, за который есть контракты."""
    if not contracts:
        return 0
    first = min(c.signed_at for c in contracts)
    start = max(appointment.started_at, first)
    end = appointment.ended_at or world.today
    return max(0, (end - start).days)


def _share(items: list[ContractFacts], predicate: Callable[[ContractFacts], bool]) -> float:
    return sum(1 for c in items if predicate(c)) / len(items)


def _young(contract: ContractFacts, world: RiskWorld) -> bool:
    company = world.company(contract.supplier_company_id)
    if company is None or company.registered_at is None:
        return False
    return 0 <= (contract.signed_at - company.registered_at).days < YOUNG_SUPPLIER_DAYS


def _nominee(contract: ContractFacts, world: RiskWorld) -> bool:
    return any(
        role.role == "director" and world.directorships_of(role.person_id) >= NOMINEE_DIRECTORSHIPS
        for role in world.staff_of(contract.supplier_company_id)
    )
