from src.modules.risk.application.interfaces.peer_anomaly_detector import (
    PeerAnomalyDetectorInterface,
)
from src.modules.risk.domain.facts import PeerAnomalyFacts
from src.modules.risk.domain.world import RiskWorld


class NoPeerAnomalyDetector(PeerAnomalyDetectorInterface):
    """R08 выключен, пока нет модели (AI-07): аномалий нет, правило молчит."""

    def detect(self, world: RiskWorld) -> list[PeerAnomalyFacts]:
        return []
