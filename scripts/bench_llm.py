"""Бенчмарк одного обращения: тот же промпт и few-shot, что у LLMAppealAnalyzer.

uv run python <this> --n 10 --out <json>   (из каталога backend, LLM_BASE_URL/LLM_MODEL из env)
"""

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import httpx

from src.modules.appeals.infrastructure.adapters.llm_analyzer import (
    SYSTEM_PROMPT,
    LLMAnswer,
    build_messages,
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--data", default="../data/generated/appeals.json")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    base = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "qwen2.5:7b-instruct")
    appeals = json.loads(Path(a.data).read_text("utf-8"))
    # Обращения средней длины: берём около медианы по длине текста.
    appeals.sort(key=lambda x: len(x["text"]))
    mid = len(appeals) // 2
    sample = appeals[mid - a.n // 2 : mid - a.n // 2 + a.n]
    schema = LLMAnswer.model_json_schema()
    system = SYSTEM_PROMPT + "\nJSON schema:\n" + json.dumps(schema)
    rows = []
    with httpx.Client(timeout=300) as client:
        # Прогрев (загрузка модели в память) — отдельно, не в статистике.
        t0 = time.perf_counter()
        client.post(
            f"{base}/chat/completions",
            json={"model": model, "messages": [{"role": "user", "content": "ok"}], "max_tokens": 1},
        ).raise_for_status()
        warmup = time.perf_counter() - t0
        for item in sample:
            msgs = [{"role": "system", "content": system}] + [
                {"role": m.role, "content": m.content} for m in build_messages(item["text"])
            ]
            t0 = time.perf_counter()
            r = client.post(
                f"{base}/chat/completions",
                json={
                    "model": model,
                    "messages": msgs,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )
            dt = time.perf_counter() - t0
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            try:
                LLMAnswer.model_validate(json.loads(content))
                valid = True
            except Exception:
                valid = False
            usage = data.get("usage", {})
            rows.append(
                {
                    "id": item["id"],
                    "chars": len(item["text"]),
                    "seconds": round(dt, 3),
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "valid": valid,
                }
            )
            print(rows[-1], flush=True)
    secs = sorted(r["seconds"] for r in rows)
    p95 = secs[min(len(secs) - 1, max(0, round(0.95 * len(secs)) - 1))]
    summary = {
        "model": model,
        "base_url": base,
        "n": len(rows),
        "warmup_seconds": round(warmup, 3),
        "mean_seconds": round(statistics.mean(secs), 3),
        "median_seconds": round(statistics.median(secs), 3),
        "p95_seconds": p95,
        "max_seconds": secs[-1],
        "valid_json": f"{sum(r['valid'] for r in rows)}/{len(rows)}",
        "mean_chars": round(statistics.mean(r["chars"] for r in rows)),
        "mean_prompt_tokens": round(statistics.mean(r["prompt_tokens"] or 0 for r in rows)),
        "mean_completion_tokens": round(statistics.mean(r["completion_tokens"] or 0 for r in rows)),
        "rows": rows,
    }
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, ensure_ascii=False))
    Path(a.out).write_text(json.dumps(summary, ensure_ascii=False, indent=2), "utf-8")


if __name__ == "__main__":
    main()
