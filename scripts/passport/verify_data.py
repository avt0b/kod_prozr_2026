"""Прогон доступных проверок проекта без внешних зависимостей.

Что запускается:
  1. unittest генератора синтетики (data/tests) — только стандартная библиотека.
  2. data.generator.check для полного набора и sample.
  3. Детерминизм генератора: повторная генерация с --seed 42 во временный каталог
     и побайтовое сравнение с data/generated.
  4. Целостность данных: внешние ключи, контрольные суммы ИНН/ОГРН, enum контракта.

Отчёт пишется в _tools/checks_report.txt и печатается в stdout.
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT.parent
REPORT = PROJECT / "dist" / "checks_report.txt"

# Консоль Windows может быть в cp1251: пишем безопасно, полный текст — в отчёте.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

log = io.StringIO()


def say(text: str = "") -> None:
    print(text.encode("ascii", "backslashreplace").decode("ascii"))
    log.write(text + "\n")


def run(args: list[str], cwd: pathlib.Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=CHILD_ENV,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def section(title: str) -> None:
    say("\n" + "=" * 78)
    say(title)
    say("=" * 78)


# --- 1. unittest генератора ---------------------------------------------------
section("1. Тесты генератора синтетики (python -m unittest data.tests.test_generator)")
os.chdir(PROJECT)
sys.path.insert(0, str(PROJECT))
loader = unittest.TestLoader()
suite = loader.loadTestsFromName("data.tests.test_generator")
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
say(stream.getvalue())
say(
    f"ИТОГ: тестов {result.testsRun}, ошибок {len(result.errors)}, "
    f"падений {len(result.failures)}, пропущено {len(result.skipped)}"
)
gen_ok = result.wasSuccessful()

# --- 2. data.generator.check --------------------------------------------------
section("2. Валидация набора данных (python -m data.generator.check)")
rc_full, out_full = run(["-m", "data.generator.check", "data/generated"], PROJECT)
say(out_full.strip())
say(f"exit code (полный набор): {rc_full}")
rc_sample, out_sample = run(
    ["-m", "data.generator.check", "data/generated/sample", "--partial"], PROJECT
)
say(out_sample.strip())
say(f"exit code (sample): {rc_sample}")

# --- 3. Детерминизм генератора -----------------------------------------------
section("3. Детерминизм: повторная генерация --seed 42 и сравнение с data/generated")
with tempfile.TemporaryDirectory() as tmp:
    rc_gen, out_gen = run(
        ["-m", "data.generator", "--seed", "42", "--out", tmp], PROJECT
    )
    say(out_gen.strip()[-2000:])
    say(f"exit code (генерация): {rc_gen}")
    same, diff, missing = [], [], []
    for src in sorted((PROJECT / "data" / "generated").glob("*.json")):
        new = pathlib.Path(tmp) / src.name
        if not new.exists():
            missing.append(src.name)
        elif new.read_bytes() == src.read_bytes():
            same.append(src.name)
        else:
            diff.append(src.name)
    say(f"побайтово совпали ({len(same)}): {', '.join(same)}")
    say(f"различаются ({len(diff)}): {', '.join(diff) or '—'}")
    say(f"не сгенерированы заново ({len(missing)}): {', '.join(missing) or '—'}")
    say("Примечание: appeals.json в git содержит LLM-предрасчёт (make precompute),")
    say("поэтому отличие по нему ожидаемо; остальные файлы должны совпадать.")
    det_ok = not diff or set(diff) <= {"appeals.json"}

# --- 4. Целостность и контрольные суммы --------------------------------------
section("4. Целостность данных: ссылки, ИНН/ОГРН, enum контракта")
DATA = PROJECT / "data" / "generated"


def load(name: str) -> list[dict]:
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def inn_ok(inn: str) -> bool:
    if not inn or not inn.isdigit():
        return False
    digits = [int(c) for c in inn]
    if len(digits) == 10:
        w = (2, 4, 10, 3, 5, 9, 4, 6, 8)
        return sum(a * b for a, b in zip(w, digits)) % 11 % 10 == digits[9]
    if len(digits) == 12:
        w1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        w2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        n1 = sum(a * b for a, b in zip(w1, digits)) % 11 % 10
        n2 = sum(a * b for a, b in zip(w2, digits)) % 11 % 10
        return n1 == digits[10] and n2 == digits[11]
    return False


def ogrn_ok(ogrn: str) -> bool:
    if not ogrn or not ogrn.isdigit():
        return False
    if len(ogrn) == 13:
        return int(ogrn[:12]) % 11 % 10 == int(ogrn[12])
    if len(ogrn) == 15:
        return int(ogrn[:14]) % 13 % 10 == int(ogrn[14])
    return False


entities = {
    name: load(name)
    for name in (
        "organs",
        "positions",
        "authorities",
        "persons",
        "appointments",
        "kinships",
        "companies",
        "company_roles",
        "employments",
        "contracts",
        "appeals",
    )
}
for name, rows in entities.items():
    say(f"{name:15} {len(rows):6} записей")

ids = {name: {r["id"] for r in rows} for name, rows in entities.items()}
fk = {
    "positions": {"organ_id": "organs"},
    "authorities": {"position_id": "positions"},
    "appointments": {"person_id": "persons", "position_id": "positions"},
    "kinships": {"person_id": "persons", "relative_id": "persons"},
    "company_roles": {"person_id": "persons", "company_id": "companies"},
    "employments": {"person_id": "persons", "company_id": "companies"},
    "contracts": {"customer_organ_id": "organs", "supplier_company_id": "companies"},
}
broken = 0
for name, links in fk.items():
    for field, target in links.items():
        bad = [r["id"] for r in entities[name] if r.get(field) not in ids[target]]
        if bad:
            broken += len(bad)
            say(f"  БИТАЯ ССЫЛКА {name}.{field} -> {target}: {len(bad)}")
say(f"битых внешних ключей: {broken}")

bad_inn_persons = [p["id"] for p in entities["persons"] if p.get("inn") and not inn_ok(p["inn"])]
bad_inn_organs = [o["id"] for o in entities["organs"] if o.get("inn") and not inn_ok(o["inn"])]
bad_inn_comp = [c["id"] for c in entities["companies"] if not inn_ok(c.get("inn", ""))]
bad_ogrn = [c["id"] for c in entities["companies"] if not ogrn_ok(c.get("ogrn", ""))]
say(f"некорректных ИНН: persons {len(bad_inn_persons)}, organs {len(bad_inn_organs)}, companies {len(bad_inn_comp)}")
say(f"некорректных ОГРН: companies {len(bad_ogrn)}")

enums = {
    ("authorities", "kind"): {"procurement", "permits", "inspection", "budget", "hr"},
    ("kinships", "kind"): {"spouse", "child", "parent", "sibling", "in_law", "other"},
    ("company_roles", "role"): {"founder", "director"},
    ("companies", "status"): {"active", "liquidating", "liquidated"},
    ("contracts", "method"): {"auction", "tender", "quotation", "single_supplier"},
    ("appeals", "channel"): {"web", "email", "letter", "hotline", "personal"},
    ("appeals", "status"): {"new", "analyzed", "routed", "closed"},
}
enum_bad = 0
for (name, field), allowed in enums.items():
    bad = [r["id"] for r in entities[name] if r.get(field) not in allowed]
    if bad:
        enum_bad += len(bad)
        say(f"  ВНЕ ENUM {name}.{field}: {len(bad)}")
say(f"значений вне enum контракта: {enum_bad}")

officials = {a["person_id"] for a in entities["appointments"]}
say(f"служащих (Person с Appointment): {len(officials)}")
truth = json.loads((DATA / "_truth" / "schemes.json").read_text(encoding="utf-8"))
positive = [t for t in truth if t.get("rule_codes")]
noise = [t for t in truth if not t.get("rule_codes")]
say(f"кейсов в _truth: всего {len(truth)}, позитивных {len(positive)}, шумовых {len(noise)}")
appeals = entities["appeals"]
pre = sum(1 for a in appeals if a.get("analysis"))
say(f"обращений: {len(appeals)}, с предрасчётом {pre}, без анализа {len(appeals) - pre}")
engines: dict[str, int] = {}
for a in appeals:
    if a.get("analysis"):
        e = a["analysis"].get("engine", "?")
        engines[e] = engines.get(e, 0) + 1
say(f"движок предрасчёта: {engines}")
dates = sorted(c["signed_at"] for c in entities["contracts"])
say(f"период контрактов: {dates[0]} — {dates[-1]}")
amounts = [c["amount"] for c in entities["contracts"]]
say(f"сумма контрактов: {sum(amounts):,.0f} ₽".replace(",", " "))

integrity_ok = broken == 0 and enum_bad == 0 and not (
    bad_inn_persons or bad_inn_organs or bad_inn_comp or bad_ogrn
)

section("СВОДКА")
say(f"тесты генератора:        {'OK' if gen_ok else 'FAIL'}")
say(f"data-check полный:       {'OK' if rc_full == 0 else 'FAIL'}")
say(f"data-check sample:       {'OK' if rc_sample == 0 else 'FAIL'}")
say(f"детерминизм генератора:  {'OK' if det_ok else 'FAIL'}")
say(f"целостность данных:      {'OK' if integrity_ok else 'FAIL'}")

REPORT.write_text(log.getvalue(), encoding="utf-8")
print(f"\nОтчёт: {REPORT}")