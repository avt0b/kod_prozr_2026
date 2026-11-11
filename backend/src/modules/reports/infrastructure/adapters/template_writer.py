"""Докладная по шаблону — без LLM. Фоллбэк для LLM-генератора и режим по умолчанию."""

from datetime import date

from src.core.utils.text import short_name
from src.modules.reports.application.interfaces.report_writer import WrittenReport
from src.modules.reports.domain.dossier import Dossier

SEVERITY_LABELS = {"high": "высокий", "medium": "средний", "low": "низкий"}


class TemplateReportWriter:
    """Реализует порт ReportWriterInterface."""

    name = "template"

    async def write(self, dossier: Dossier) -> WrittenReport:
        return WrittenReport(text=render_report(dossier), generator=self.name)


def render_report(dossier: Dossier, today: date | None = None) -> str:
    today = today or date.today()
    position = ", ".join(
        part for part in (dossier.position_title, dossier.department, dossier.organ_name) if part
    )
    lines = [
        "ДОКЛАДНАЯ ЗАПИСКА",
        f"от {today:%d.%m.%Y}",
        "",
        "О результатах анализа сведений на предмет возможного конфликта интересов",
        "",
        "В ходе информационно-аналитической работы проанализированы сведения о служащем: "
        f"{dossier.full_name}" + (f" ({position})" if position else "") + ".",
        "",
    ]
    if not dossier.has_flags:
        lines.append(
            "Признаков возможного конфликта интересов по правилам системы не выявлено "
            f"(риск-балл {dossier.score:g} из 100)."
        )
    else:
        lines.append(
            f"Выявлены признаки, которые могут свидетельствовать о наличии конфликта интересов "
            f"(риск-балл {dossier.score:g} из 100):"
        )
        lines.append("")
        for number, flag in enumerate(dossier.flags, start=1):
            level = SEVERITY_LABELS.get(flag.severity, flag.severity)
            lines.append(f"{number}. [{flag.rule_code}, уровень — {level}] {flag.explanation}")
            if flag.evidence:
                lines.append(f"   Цепочка связей: {' → '.join(flag.evidence)}.")
            if flag.legal_ref:
                lines.append(f"   Норма: {flag.legal_ref}.")
        lines += [
            "",
            "Предлагается:",
            f"1. Запросить у {short_name(dossier.full_name)} пояснения "
            "по указанным обстоятельствам.",
            "2. Проверить наличие уведомлений о возникновении личной заинтересованности.",
            "3. При подтверждении сведений рассмотреть вопрос на заседании комиссии "
            "по соблюдению требований к служебному поведению и урегулированию конфликта интересов.",
        ]
    return "\n".join(lines)
