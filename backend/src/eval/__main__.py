"""AI-08: оценка качества на синтетике (`make eval`, docs/ai.md §7).

    python -m src.eval --dir ../data/generated --out ../eval/report.json [--llm] [--limit N]

Нужна БД после `make seed`: флаги и баллы берутся из неё, справочник служащих — для
сопоставления лиц. Обращения разбираются заново: фоллбэк всегда, LLM — с --llm и заданным
LLM_BASE_URL. Метрики получены на синтетике, где схемы заложены нами: оценка верхняя.
"""

import argparse
import asyncio
import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.core.config import BASE_DIR, get_settings_from_env
from src.core.infrastructure.database.database import get_async_session_maker, get_engine
from src.core.infrastructure.llm import OpenAICompatibleLLMClient
from src.core.infrastructure.logger import configure_logging
from src.core.utils.json_files import read_models
from src.modules.appeals.application.interfaces.appeal_analyzer import AppealAnalyzer
from src.modules.appeals.application.services.appeal_analysis import AppealAnalysisService
from src.modules.appeals.infrastructure.adapters.fallback_analyzer import FallbackAppealAnalyzer
from src.modules.appeals.infrastructure.adapters.llm_analyzer import LLMAppealAnalyzer
from src.modules.appeals.infrastructure.adapters.rule_based_analyzer import (
    RuleBasedAppealAnalyzer,
)
from src.modules.appeals.presentation.dependencies import get_person_matcher
from src.modules.appeals.presentation.schemas.seed import AppealSeed
from src.web import wiring

RULES = ("R01", "R02", "R03", "R04", "R05", "R06")
CATEGORIES = ("bribe", "conflict_of_interest", "procurement", "abuse_of_power")
SIGNAL_CODES = (
    "named_official", "named_position", "named_organization", "money_amount", "specific_date",
    "procurement_ref", "relative_mentioned", "extortion", "evidence_available", "vague_no_facts",
)  # fmt: skip


def prf(tp: int, fp: int, fn: int) -> dict[str, float | int]:
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


# ------------------------------------------------------------------ rules (DB after seed)
async def rules_metrics(session: Any, truth: dict[str, Any]) -> dict[str, Any]:
    rows = (await session.execute(text("select person_id, rule_code from risk.flags"))).all()
    flagged: dict[str, set[str]] = defaultdict(set)
    for person_id, rule in rows:
        flagged[str(person_id)].add(rule)
    expected: dict[str, set[str]] = defaultdict(set)
    for scheme in truth["schemes"]:
        expected[scheme["person_id"]] |= set(scheme["rule_codes"])
    per_rule = {}
    for rule in RULES:
        got = {p for p, rules in flagged.items() if rule in rules}
        want = {p for p, rules in expected.items() if rule in rules}
        per_rule[rule] = prf(len(got & want), len(got - want), len(want - got))
    noise = [s for s in truth["schemes"] if not s["rule_codes"]]
    noise_clean = sum(
        1 for s in noise if not (flagged[s["person_id"]] & set(RULES)) - expected[s["person_id"]]
    )
    peers = {item["person_id"] for item in truth["peer_anomalies"]}
    r08 = {p for p, rules in flagged.items() if "R08" in rules}
    positives = {p for p, rules in expected.items() if rules}
    scores = (
        await session.execute(
            text("select person_id from risk.scores order by score desc, flags_count desc")
        )
    ).all()
    ranking = [str(r[0]) for r in scores]
    planted = {
        p for p, rules in expected.items() if rules & {"R01", "R02", "R03", "R04", "R05", "R08"}
    }
    return {
        "per_rule": per_rule,
        "noise_cases": {"total": len(noise), "without_false_flags": noise_clean},
        "R08": {
            "recall": round(len(r08 & peers) / len(peers), 3) if peers else None,
            "found": len(r08 & peers),
            "planted": len(peers),
            "flags_on_clean_officials": len(r08 - positives),
        },
        "ranking": {
            f"precision@{n}": round(len(set(ranking[:n]) & planted) / n, 3) for n in (10, 20)
        },
    }


# ------------------------------------------------------------------ appeals
async def appeals_metrics(
    session: Any, data_dir: Path, truth: dict[str, Any], analyzer: AppealAnalyzer, limit: int | None
) -> dict[str, Any]:
    labels = {label["appeal_id"]: label for label in truth["appeals_labels"]}
    seeds = read_models(AppealSeed, data_dir / "appeals.json")
    if limit:
        seeds = seeds[:limit]
    service = AppealAnalysisService(
        analyzer, wiring.appeals_person_directory(session), get_person_matcher()
    )
    corruption = Counter[str]()
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    link = Counter[str]()
    signals: dict[str, Counter[str]] = defaultdict(Counter)
    injection = Counter[str]()
    engines = Counter[str]()
    durations: list[float] = []
    candidates_only = 0
    for seed in seeds:
        label = labels[str(seed.id)]
        appeal = seed.model_copy(update={"analysis": None, "status": "new"}).to_entity()
        started = time.perf_counter()
        analysis = await analyzer.analyze(appeal.text)
        durations.append(time.perf_counter() - started)
        match = await service.match(analysis, appeal)
        engines[analysis.engine] += 1
        want, got = label["is_corruption"], analysis.is_corruption
        corruption["tp" if want and got else "fp" if got else "fn" if want else "tn"] += 1
        if want:
            confusion[label["category"]][analysis.category.value] += 1
        want_links = set(label["linked_person_ids"])
        got_links = {str(p) for p in match.linked}
        link["tp"] += len(want_links & got_links)
        link["fp"] += len(got_links - want_links)
        link["fn"] += len(want_links - got_links)
        if match.candidates and not match.linked:
            candidates_only += 1
        codes = analysis.signal_codes
        for code in SIGNAL_CODES:
            truth_has, got_has = code in label["signals"], code in codes
            key = "tp" if truth_has and got_has else "fp" if got_has else "fn" if truth_has else ""
            if key:
                signals[code][key] += 1
        if label["injection"]:
            injection["total"] += 1
            injection["intact"] += int(got == want)
    f1s = []
    for category in CATEGORIES:
        tp = confusion[category][category]
        fp = sum(confusion[c][category] for c in CATEGORIES if c != category)
        fn = sum(n for c, n in confusion[category].items() if c != category)
        f1s.append(prf(tp, fp, fn)["f1"])
    durations.sort()
    return {
        "appeals": len(seeds),
        "engines": dict(engines),
        "is_corruption": prf(corruption["tp"], corruption["fp"], corruption["fn"]),
        "category_macro_f1": round(sum(f1s) / len(f1s), 3),
        "category_confusion": {k: dict(v) for k, v in confusion.items()},
        "linking": {
            **prf(link["tp"], link["fp"], link["fn"]),
            "candidates_without_link_share": round(candidates_only / len(seeds), 3),
        },
        "signals": {
            code: prf(c["tp"], c["fp"], c["fn"]) for code, c in signals.items() if sum(c.values())
        },
        "injection_intact": f"{injection['intact']}/{injection['total']}",
        "seconds": {
            "median": round(statistics.median(durations), 3),
            "p95": round(durations[max(0, int(len(durations) * 0.95) - 1)], 3),
        },
    }


# ------------------------------------------------------------------ report
def print_report(report: dict[str, Any]) -> None:
    rules = report["rules"]
    print("\nПравила (по парам служащий × правило, против _truth/schemes.json)")
    print(f"{'Правило':<8}{'P':>7}{'R':>7}{'F1':>7}{'TP':>5}{'FP':>5}{'FN':>5}")
    for rule, m in rules["per_rule"].items():
        print(
            f"{rule:<8}{m['precision']:>7}{m['recall']:>7}{m['f1']:>7}"
            f"{m['tp']:>5}{m['fp']:>5}{m['fn']:>5}"
        )
    noise = rules["noise_cases"]
    clean = f"{noise['without_false_flags']}/{noise['total']}"
    print(f"Ложноположительные кейсы без лишних флагов: {clean}")
    r08 = rules["R08"]
    print(
        f"R08: recall {r08['recall']} ({r08['found']}/{r08['planted']}), "
        f"флагов на «чистых» служащих: {r08['flags_on_clean_officials']}"
    )
    print(f"Рейтинг: {rules['ranking']}")
    for engine, m in report["appeals"].items():
        print(f"\nОбращения — {engine} ({m['appeals']} шт., движки {m['engines']})")
        c = m["is_corruption"]
        print(f"  is_corruption: P {c['precision']} R {c['recall']} F1 {c['f1']}")
        print(f"  категория (macro-F1): {m['category_macro_f1']}")
        link = m["linking"]
        print(
            f"  привязка лиц: P {link['precision']} R {link['recall']}, "
            f"только кандидаты: {link['candidates_without_link_share']}"
        )
        print(f"  prompt injection без поломки разметки: {m['injection_intact']}")
        print(f"  время анализа, с: медиана {m['seconds']['median']}, p95 {m['seconds']['p95']}")
        weak = {k: v["f1"] for k, v in m["signals"].items()}
        print(f"  сигналы (F1): {weak}")


async def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings_from_env()
    data_dir = Path(args.dir)
    if not data_dir.is_absolute():
        data_dir = BASE_DIR / data_dir
    truth = {
        name: json.loads((data_dir / "_truth" / f"{name}.json").read_text("utf-8"))
        for name in ("schemes", "appeals_labels", "peer_anomalies")
    }
    engine = get_engine(settings.database_url)
    llm = (
        OpenAICompatibleLLMClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value() if settings.llm_api_key else None,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        )
        if args.llm and settings.llm_base_url
        else None
    )
    report: dict[str, Any] = {"data": str(data_dir), "note": "метрики на синтетике: оценка верхняя"}
    try:
        async with get_async_session_maker(engine)() as session:
            report["rules"] = await rules_metrics(session, truth)
            rules = RuleBasedAppealAnalyzer()
            report["appeals"] = {
                "fallback": await appeals_metrics(session, data_dir, truth, rules, args.limit)
            }
            if llm is not None:
                analyzer = FallbackAppealAnalyzer(LLMAppealAnalyzer(llm, settings.llm_model), rules)
                report["appeals"][f"llm:{settings.llm_model}"] = await appeals_metrics(
                    session, data_dir, truth, analyzer, args.limit
                )
    finally:
        if llm is not None:
            await llm.aclose()
        await engine.dispose()
    return report


def main() -> None:
    configure_logging("WARNING")
    parser = argparse.ArgumentParser(prog="python -m src.eval", description=__doc__)
    parser.add_argument("--dir", default=get_settings_from_env().seed_dir)
    parser.add_argument("--out", default="../eval/report.json")
    parser.add_argument("--llm", action="store_true", help="оценить и LLM (нужен LLM_BASE_URL)")
    parser.add_argument("--limit", type=int, default=None, help="первые N обращений")
    args = parser.parse_args()
    report = asyncio.run(run(args))
    print_report(report)
    out = Path(args.out)
    if not out.is_absolute():
        out = BASE_DIR / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nОтчёт: {out}")


if __name__ == "__main__":
    main()
