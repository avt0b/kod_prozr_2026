"""R03–R06, R08: заготовки. Сигнатура и место в движке готовы, логика — TODO.

R01, R02, R07 реализованы в отдельных файлах rules/r0N_*.py.

Каждое правило возвращает [] — движок их уже вызывает, так что реализация не требует
правок вокруг: только тело evaluate + юнит-тест в tests/unit/risk/.
"""

from src.modules.risk.domain.enums import RuleCode, Severity
from src.modules.risk.domain.facts import OfficialFacts
from src.modules.risk.domain.flag import RiskFlag
from src.modules.risk.domain.rules.base import RiskRule
from src.modules.risk.domain.world import RiskWorld

EX_EMPLOYER_YEARS = 3


class ExEmployerSupplierRule(RiskRule):
    """R03. Бывший работодатель служащего (работа закончилась ≤ 3 лет назад) — подрядчик
    его органа.

    TODO:
      * для каждого official.employments с ended_at не раньше чем (дата контракта - 3 года);
      * world.contracts_between(appointment.organ_id, employment.company_id), подписанные
        в период назначения;
      * evidence: служащий -> компания (employment) -> контракты -> орган.
    """

    code = RuleCode.R03
    name = "ex_employer_supplier"
    severity = Severity.MEDIUM
    legal_ref = "273-ФЗ ст. 10"

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        return []


class RevolvingDoorRule(RiskRule):
    """R04. После увольнения служащий перешёл в компанию, которая была в сфере его полномочий.

    TODO:
      * завершённые назначения (ended_at не None) с полномочиями procurement/permits/inspection;
      * employments, начавшиеся после ended_at (≤ 2 лет, ст. 12 273-ФЗ);
      * компания была контрагентом органа в период назначения
        (world.contracts_between(organ_id, company_id)).
      * В RiskWorld сейчас грузятся только действующие служащие — для R04 нужно
        расширить world_loader бывшими (у кого все назначения закрыты).
    """

    code = RuleCode.R04
    name = "revolving_door"
    severity = Severity.MEDIUM
    legal_ref = "273-ФЗ ст. 12"

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        return []


class SharedContactsRule(RiskRule):
    """R05. У компании-подрядчика органа тот же адрес или телефон, что у служащего/родственника.

    TODO:
      * нормализовать телефон (только цифры, последние 10) и адрес (нижний регистр,
        без «ул.», «д.», пробелов) — функция-нормализатор в domain/;
      * компании-подрядчики органов служащего: world.contracts_of_organ(organ_id);
      * совпадение с official.person / relative.person (address, phone).
    """

    code = RuleCode.R05
    name = "shared_contacts"
    severity = Severity.MEDIUM
    legal_ref = "273-ФЗ ст. 10"

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        return []


class SupplierConcentrationRule(RiskRule):
    """R06. Аномальная доля одного поставщика в закупках в сфере полномочий служащего.

    TODO:
      * контракты органа (world.contracts_of_organ) в периоды назначения и в сфере ОКПД2
        полномочия procurement;
      * доля поставщика по сумме > порога (например 50% при ≥ 5 контрактах) или
        индекс Херфиндаля-Хиршмана > 0.25;
      * explanation с долей и суммой, evidence: служащий -> орган -> поставщик.
    """

    code = RuleCode.R06
    name = "supplier_concentration"
    severity = Severity.LOW
    legal_ref = None

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        return []


class PeerAnomalyRule(RiskRule):
    """R08. Аномалия относительно коллег той же должности и региона (ML).

    TODO:
      * признаки на служащего: число связанных компаний, сумма контрактов связанных компаний,
        число родственников-предпринимателей, флаги R01–R07;
      * группы коллег: (position_title, регион органа) — нужен регион в AppointmentFacts;
      * z-score / IsolationForest по группе; флаг при |z| > 3, severity low/medium.
      * Тяжёлую модель обучать офлайн, в правило передавать готовые оценки через RiskWorld.
    """

    code = RuleCode.R08
    name = "peer_anomaly"
    severity = Severity.LOW
    legal_ref = None

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        return []
