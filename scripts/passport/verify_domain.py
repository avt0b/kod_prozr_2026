"""Проверки доменной логики на чистом Python (без зависимостей бэкенда).

1. ScorePolicy (backend/src/modules/risk/domain/score.py) — методика балла:
   веса ADR-16, вклад правила, потолок, ограничение 0..100.
   Импортируется напрямую через importlib, чтобы не тянуть пакет src.
2. Формулы разбора обращений: specificity и маршрутизация (docs/ai.md §2)
   и severity R07 (§3) — сверка с фактическим предрасчётом data/generated.
3. Согласованность предрасчёта: 105 обращений разобраны LLM, демо-обращение new.

Отчёт: _tools/domain_checks_report.txt
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import sys
import types

PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT.parent
DATA = PROJECT / "data" / "generated"
REPORT = PROJECT / "dist" / "domain_checks_report.txt"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
log = io.StringIO()


def say(text: str = "") -> None:
    print(text.encode("ascii", "backslashreplace").decode("ascii"))
    log.write(text + "\n")


def section(title: str) -> None:
    say("\n" + "=" * 78)
    say(title)
    say("=" * 78)


def load_module(name: str, path: pathlib.Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


failures: list[str] = []


def check(label: str, got: object, want: object) -> None:
    ok = got == want
    say(f"  [{'OK' if ok else 'FAIL'}] {label}: {got!r} (ожидалось {want!r})")
    if not ok:
        failures.append(label)


# --- 1. ScorePolicy ----------------------------------------------------------
section("1. Методика риск-балла (ScorePolicy, ADR-04/ADR-16)")
RISK = PROJECT / "backend" / "src" / "modules" / "risk" / "domain"
# Пакет-заглушка, чтобы относительные импорты score.py разрешились без src.*
pkg = types.ModuleType("riskdomain")
pkg.__path__ = [str(RISK)]
sys.modules["riskdomain"] = pkg
enums = load_module("riskdomain.enums", RISK / "enums.py")
flag_mod_path = RISK / "flag.py"
say(f"enums: RuleCode={len(list(enums.RuleCode))}, Severity={[s.value for s in enums.Severity]}")

# score.py импортирует src.modules.risk.domain.{enums,flag}; подменяем префикс.
src_text = (RISK / "score.py").read_text(encoding="utf-8")
src_text = src_text.replace("from src.modules.risk.domain.", "from riskdomain.")
flag_text = flag_mod_path.read_text(encoding="utf-8")
flag_text = flag_text.replace("from src.modules.risk.domain.", "from riskdomain.")
for name, text in (("riskdomain.flag", flag_text), ("riskdomain.score", src_text)):
    mod = types.ModuleType(name)
    mod.__package__ = "riskdomain"
    sys.modules[name] = mod
    exec(compile(text, name, "exec"), mod.__dict__)

score_mod = sys.modules["riskdomain.score"]
flag_mod = sys.modules["riskdomain.flag"]
Severity = enums.Severity
RuleCode = enums.RuleCode
ScorePolicy = score_mod.ScorePolicy
policy = ScorePolicy()

check("вес high", policy.weight_for(Severity.HIGH), 40.0)
check("вес medium", policy.weight_for(Severity.MEDIUM), 20.0)
check("вес low", policy.weight_for(Severity.LOW), 5.0)
check("вес R08 low", policy.weight_for(Severity.LOW, RuleCode.R08), 3.0)
check("вес R08 medium", policy.weight_for(Severity.MEDIUM, RuleCode.R08), 5.0)
check("вклад одного high", policy.rule_contribution([40.0]), 40.0)
check("вклад 10 однотипных high (потолок 2 веса)", policy.rule_contribution([40.0] * 10), 80.0)
check("вклад high+low", policy.rule_contribution([40.0, 5.0]), 42.5)
check("инвариант ADR-16: 2 low + R08 medium <= medium-5",
      policy.weight_for(Severity.LOW) * 2 + policy.weight_for(Severity.MEDIUM, RuleCode.R08) <= 15.0,
      True)
check("R08 не тяжелее самого лёгкого правила",
      max(policy.weight_for(s, RuleCode.R08) for s in Severity) <= policy.weight_for(Severity.LOW),
      True)


def make_flag(rule: RuleCode, severity: Severity):
    weight = policy.weight_for(severity, rule)
    return flag_mod.RiskFlag(
        person_id=__import__("uuid").uuid4(),
        rule_code=rule,
        rule_name=rule.value,
        severity=severity,
        weight=weight,
        explanation="проверочный флаг",
        evidence=({"node_id": "x", "type": "person", "label": "узел"},),
        legal_ref=None,
    )


from datetime import UTC, datetime  # noqa: E402

now = datetime(2026, 11, 22, tzinfo=UTC)
pid = __import__("uuid").uuid4()


def score_of(flags) -> float:
    return score_mod.ScorePolicy().score(pid, flags, now).score


s_high = score_of([make_flag(RuleCode.R01, Severity.HIGH)])
check("балл: один R01 high", s_high, 40.0)
s_two = score_of([make_flag(RuleCode.R01, Severity.HIGH), make_flag(RuleCode.R02, Severity.HIGH)])
check("балл: две разные схемы high", s_two, 80.0)
s_many = score_of([make_flag(RuleCode.R01, Severity.HIGH) for _ in range(10)])
check("балл: 10 однотипных R01 (потолок правила)", s_many, 80.0)
s_cap = score_of([make_flag(r, Severity.HIGH) for r in (RuleCode.R01, RuleCode.R02, RuleCode.R03)])
check("балл: ограничен 100", s_cap, 100.0)
s_ml = score_of([make_flag(RuleCode.R08, Severity.MEDIUM)])
check("балл: R08 medium в одиночку", s_ml, 5.0)
s_vague = score_of([make_flag(RuleCode.R07, Severity.LOW)])
check("балл: одно расплывчатое обращение (R07 low)", s_vague, 5.0)
check("ML в одиночку не выводит в топ (>40 недопустимо)", s_ml < 40.0, True)

# --- 2. Формулы разбора обращений на фактическом предрасчёте ------------------
section("2. Формулы разбора обращений против фактического предрасчёта (docs/ai.md)")
appeals = json.loads((DATA / "appeals.json").read_text(encoding="utf-8"))


def specificity_of(signals: set[str]) -> float:
    s = 0.0
    if "named_official" in signals or "named_position" in signals:
        s += 0.30
    if "named_organization" in signals:
        s += 0.20
    if "money_amount" in signals:
        s += 0.20
    if "specific_date" in signals:
        s += 0.15
    if "procurement_ref" in signals or "evidence_available" in signals:
        s += 0.15
    if "vague_no_facts" in signals:
        s *= 0.5
    return round(s, 4)


def route_of(is_corruption: bool, category: str, signals: set[str], spec: float) -> str:
    if not is_corruption:
        return "Рассмотрение по компетенции в общем порядке"
    base = "Подразделение по профилактике коррупционных правонарушений"
    if (category == "bribe" or "extortion" in signals) and spec >= 0.6:
        return base + "|правоохранительные"
    return base


spec_bad, route_bad, closed_bad = 0, 0, 0
allowed_signals = {
    "named_official", "named_position", "named_organization", "money_amount",
    "specific_date", "procurement_ref", "relative_mentioned", "extortion",
    "evidence_available", "repeated_subject", "vague_no_facts",
}
allowed_categories = {"bribe", "conflict_of_interest", "procurement", "abuse_of_power", "other"}
engines: dict[str, int] = {}
r07_severity_bad = 0
for a in appeals:
    an = a.get("analysis")
    if not an:
        continue
    engines[an.get("engine", "?")] = engines.get(an.get("engine", "?"), 0) + 1
    codes = {s["code"] for s in an.get("signals", [])}
    if codes - allowed_signals:
        closed_bad += 1
    if an.get("category") not in allowed_categories:
        closed_bad += 1
    if abs(specificity_of(codes) - round(float(an.get("specificity", 0)), 4)) > 1e-6:
        spec_bad += 1
    want_route = route_of(an["is_corruption"], an["category"], codes, float(an["specificity"]))
    got_route = an.get("route_to", "")
    if want_route.endswith("|правоохранительные"):
        if not got_route.startswith("Подразделение по профилактике"):
            route_bad += 1
    elif got_route != want_route:
        route_bad += 1

say(f"  обращений с анализом: {sum(engines.values())}, движки: {engines}")
check("specificity совпадает с формулой во всех обращениях", spec_bad, 0)
check("route_to совпадает с таблицей маршрутизации", route_bad, 0)
check("сигналы и категории только из закрытых списков", closed_bad, 0)

# R07: s = сумма confidence*specificity по привязанным коррупционным обращениям
by_person: dict[str, float] = {}
for a in appeals:
    an = a.get("analysis")
    if not an or not an.get("is_corruption"):
        continue
    for pid_ in a.get("linked_person_ids", []):
        by_person[pid_] = by_person.get(pid_, 0.0) + float(an["confidence"]) * float(an["specificity"])


def r07_severity(s: float) -> str:
    return "low" if s < 0.8 else ("medium" if s < 1.6 else "high")


dist = {"low": 0, "medium": 0, "high": 0}
for s in by_person.values():
    dist[r07_severity(s)] += 1
say(f"  служащих с привязанными коррупционными обращениями: {len(by_person)}")
say(f"  расчётная severity R07 по формуле: {dist}")
truth = json.loads((DATA / "_truth" / "meta.json").read_text(encoding="utf-8"))
h1 = truth["cases"]["H1"]
n1 = truth["cases"]["N1"]
say(f"  H1 (Соколов): s={by_person.get(h1, 0):.3f} -> {r07_severity(by_person.get(h1, 0.0))}")
say(f"  N1 (Орлов, ложное обвинение): s={by_person.get(n1, 0):.3f} -> {r07_severity(by_person.get(n1, 0.0))}")
check("ложное обвинение N1 не выше low", r07_severity(by_person.get(n1, 0.0)), "low")

# --- 3. Демо-обращение -------------------------------------------------------
section("3. Состояние демо-обращения и предрасчёта")
new = [a for a in appeals if a.get("status") == "new"]
check("ровно одно обращение оставлено new для живого демо", len(new), 1)
demo_ids = set(truth["demo_appeal_ids"])
check("new — это именно демо-обращение", {a["id"] for a in new} <= demo_ids, True)
check("все остальные разобраны LLM", engines, {"llm": 105})

section("СВОДКА")
say(f"проверок провалено: {len(failures)}")
if failures:
    say("проваленные: " + "; ".join(failures))
say("ИТОГ: " + ("OK" if not failures else "FAIL"))
REPORT.write_text(log.getvalue(), encoding="utf-8")
print(f"\nОтчёт: {REPORT}")
sys.exit(1 if failures else 0)