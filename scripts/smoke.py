"""Smoke-тест стенда (OPS-06): все эндпоинты контракта, коды ответов и ключевые поля.

    python3 scripts/smoke.py [--api http://localhost:8000] [--keep-demo]

Создаёт демо-обращение H1 и проверяет, что балл Соколова вырос и он вышел на 1-е место.
Это меняет данные: перед показом снова `make reset` (или используйте --keep-demo, чтобы
демо-обращение не отправлялось). Только стандартная библиотека Python.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEMO_TEXT_FILE = ROOT / "demo" / "appeal_h1.txt"


class Smoke:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.failures: list[str] = []
        self.checks = 0

    def call(
        self, method: str, path: str, body: Any = None, expect: int = 200, timeout: float = 60
    ) -> Any:
        url = self.base + urllib.parse.quote(path, safe="/?&=:-_.")
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            url, data=data, method=method, headers={"Content-Type": "application/json"}
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        except (urllib.error.URLError, TimeoutError) as error:
            self.fail(f"{method} {path}: нет ответа ({error})")
            return None
        elapsed = time.perf_counter() - started
        ok = status == expect
        print(f"{'OK  ' if ok else 'FAIL'} {method:<4} {path:<60} {status} {elapsed * 1000:6.0f} мс")
        self.checks += 1
        if not ok:
            self.failures.append(f"{method} {path}: {status}, ожидалось {expect}")
        try:
            return json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return raw.decode(errors="replace")

    def expect(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.fail(message)

    def fail(self, message: str) -> None:
        print(f"FAIL {message}")
        self.failures.append(message)


def keys(data: Any, *names: str) -> bool:
    return isinstance(data, dict) and all(name in data for name in names)


def run(api: str, send_demo: bool) -> Smoke:
    s = Smoke(api)
    v1 = "/api/v1"
    health = s.call("GET", "/health")
    s.expect(health == {"status": "ok"}, "/health: ожидалось {'status': 'ok'}")

    stats = s.call("GET", f"{v1}/stats/overview")
    s.expect(
        keys(stats, "officials_total", "officials_with_flags", "flags_by_severity",
             "appeals_total", "appeals_by_status", "computed_at"),
        "/stats/overview: нет полей контракта",
    )  # fmt: skip
    s.expect(bool(stats) and stats.get("officials_total", 0) >= 100, "мало служащих: сиды не загружены?")

    organs = s.call("GET", f"{v1}/organs")
    s.expect(keys(organs, "items", "total") and organs["total"] >= 1, "/organs: пусто")

    rating = s.call("GET", f"{v1}/officials?limit=20")
    s.expect(keys(rating, "items", "total") and len(rating["items"]) > 0, "/officials: пусто")
    if rating and rating.get("items"):
        item = rating["items"][0]
        s.expect(
            keys(item, "id", "full_name", "position", "organ", "organ_id", "risk_score", "top_flags"),
            "/officials: нет полей элемента",
        )
        scores = [i["risk_score"] for i in rating["items"]]
        s.expect(scores == sorted(scores, reverse=True), "/officials: не отсортировано по баллу")
    for query in ("sort=full_name", "min_score=40", "rule_code=R02", "query=Соколов"):
        s.call("GET", f"{v1}/officials?{query}&limit=5")
    s.call("GET", f"{v1}/officials?limit=1000", expect=422)

    found = s.call("GET", f"{v1}/officials?query=Соколов&limit=5") or {"items": []}
    h1 = next((i for i in found["items"] if i["full_name"] == "Соколов Андрей Викторович"), None)
    if h1 is None:
        s.fail("демо-кейс H1 (Соколов Андрей Викторович) не найден")
        return s
    pid = h1["id"]
    profile = s.call("GET", f"{v1}/officials/{pid}")
    s.expect(
        keys(profile, "person", "appointments", "authorities", "relatives", "companies", "risk"),
        "профиль H1: нет разделов контракта",
    )
    if profile:
        names = {c["company"]["name"] for c in profile.get("companies", [])}
        s.expect("ООО «ДорСтройРесурс»" in names, "профиль H1: нет ООО «ДорСтройРесурс»")
    graph = s.call("GET", f"{v1}/officials/{pid}/graph?depth=2")
    s.expect(keys(graph, "nodes", "edges") and len(graph["nodes"]) > 3, "граф H1 пуст")
    flags = s.call("GET", f"{v1}/officials/{pid}/flags")
    codes = {f["rule_code"] for f in (flags or {}).get("items", [])}
    s.expect({"R01", "R05", "R06"} <= codes, f"флаги H1: {sorted(codes)}, ожидались R01, R05, R06")
    if graph and flags:
        node_ids = {n["id"] for n in graph["nodes"]}
        evidence = {e["node_id"] for f in flags["items"] for e in f["evidence"]}
        s.expect(evidence <= node_ids, "evidence флагов H1 не входит в граф")
    s.call("GET", f"{v1}/officials/00000000-0000-0000-0000-000000000000", expect=404)

    recompute = s.call("POST", f"{v1}/risk/recompute", timeout=120)
    s.expect(keys(recompute, "officials_processed", "flags_total", "computed_at"), "recompute: поля")

    appeals = s.call("GET", f"{v1}/appeals?limit=20")
    s.expect(keys(appeals, "items", "total") and appeals["total"] >= 50, "/appeals: мало обращений")
    s.call("GET", f"{v1}/appeals?status=analyzed&category=procurement&limit=5")
    if appeals and appeals.get("items"):
        appeal = s.call("GET", f"{v1}/appeals/{appeals['items'][0]['id']}")
        s.expect(keys(appeal, "analysis", "linked_persons"), "/appeals/{id}: нет полей")

    report = s.call("POST", f"{v1}/reports", {"person_id": pid}, expect=201, timeout=180)
    if keys(report, "id", "text"):
        s.expect("Решение принимает" in report["text"], "докладная без обязательной пометки")
        s.call("GET", f"{v1}/reports/{report['id']}")
    audit = s.call("GET", f"{v1}/audit?object_id={pid}&limit=5")
    s.expect(keys(audit, "items", "total") and audit["total"] > 0, "журнал H1 пуст")
    answer = s.call(
        "POST",
        f"{v1}/assistant/ask",
        {"question": "Покажи служащих, у которых родственники среди подрядчиков их органа"},
        timeout=180,
    )
    s.expect(keys(answer, "answer", "sources"), "/assistant/ask: нет полей")

    if send_demo:
        text = DEMO_TEXT_FILE.read_text("utf-8").strip()
        before = h1["risk_score"]
        created = s.call(
            "POST", f"{v1}/appeals", {"text": text, "channel": "web"}, expect=201, timeout=180
        )
        if keys(created, "id", "analysis", "linked_person_ids"):
            s.expect(pid in created["linked_person_ids"], "демо-обращение не привязано к H1")
            s.call("POST", f"{v1}/appeals/{created['id']}/reanalyze", timeout=180)
        top = s.call("GET", f"{v1}/officials?limit=1") or {"items": [{}]}
        leader = top["items"][0] if top.get("items") else {}
        after = leader.get("risk_score", 0)
        print(f"     Балл H1: {before} → {after if leader.get('id') == pid else '—'}")
        s.expect(leader.get("id") == pid and after > before, "после демо-обращения H1 не на 1-м месте")
    return s


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--keep-demo", action="store_true", help="не отправлять демо-обращение")
    args = parser.parse_args()
    smoke = run(args.api, send_demo=not args.keep_demo)
    if smoke.failures:
        print(f"\nsmoke: {len(smoke.failures)} ошибок из {smoke.checks} проверок")
        sys.exit(1)
    print(f"\nsmoke: OK, {smoke.checks} проверок")


if __name__ == "__main__":
    main()
