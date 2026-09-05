"""Run sample questions through a local ResearchLoop or the HTTP API."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]


def answer_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return str(result.get("answer", result))
    return str(getattr(result, "answer", result))


async def run_http(question: str, api_url: str) -> Any:
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(f"{api_url.rstrip('/')}/ask", json={"question": question})
        response.raise_for_status()
        return response.json()


def run_local(question: str) -> Any:
    from gestaltx.agent.loop import ResearchLoop

    loop = ResearchLoop()
    result = loop.run(question)
    if asyncio.iscoroutine(result):
        return asyncio.run(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("local", "http"), default="local")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--questions", type=Path, default=ROOT / "eval/questions/sample_questions.json")
    parser.add_argument("--golden", type=Path, default=ROOT / "eval/golden/1c_answers.json")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    golden = json.loads(args.golden.read_text(encoding="utf-8"))
    rows = []
    for item in questions:
        if item["question"].startswith("["):
            rows.append({"id": item["id"], "status": "skipped", "answer": "prompt unavailable"})
            continue
        try:
            result = asyncio.run(run_http(item["question"], args.api_url)) if args.mode == "http" else run_local(item["question"])
            actual = answer_text(result)
            expected = golden.get(item["id"], {}).get("answer")
            passed = expected is None or expected.lower() in actual.lower()
            rows.append({"id": item["id"], "status": "pass" if passed else "fail", "answer": actual, "expected": expected})
        except Exception as exc:
            rows.append({"id": item["id"], "status": "error", "answer": f"{type(exc).__name__}: {exc}"})

    destination = args.report or ROOT / "eval/reports/latest.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# GestaltX evaluation", "", f"Generated: {datetime.now(timezone.utc).isoformat()}", ""]
    lines.extend(f"- **{row['id']}** — {row['status']}: {row['answer']}" for row in rows)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(destination)
    return 1 if any(row["status"] in {"fail", "error"} for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
