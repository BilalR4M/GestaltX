"""FastAPI application for question answering and live traces."""

from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .runtime import Runtime, get_runtime


SAMPLE_QUESTIONS = [
    "When was Gloamreach founded?",
    "Who forged the Ashen Crown?",
    "What sources disagree about the founding of Gloamreach?",
]


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    evidence: list[dict[str, Any]] | None = None


def create_app(
    runtime: Runtime | None = None,
    *,
    runtime_factory: Callable[[], Runtime] = get_runtime,
) -> FastAPI:
    def active_runtime() -> Runtime:
        return runtime or runtime_factory()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            active_runtime().start_corpus_watcher()
        except Exception:  # noqa: BLE001
            pass
        yield

    app = FastAPI(title="GestaltX API", version="1.0.0", lifespan=lifespan)
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    config = getattr(runtime, "config", None) if runtime is not None else None
    if config is not None:
        origins = getattr(getattr(config, "app", None), "cors_origins", origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        current = active_runtime()
        corpus = current.corpus_status
        return {
            "status": "ok",
            "index_ready": current.ready,
            "mode": "indexed" if current.ready else "local",
            "llm": current.llm_status,
            "corpus_version": corpus.get("version", 0),
        }

    @app.get("/api/corpus")
    def corpus() -> dict[str, Any]:
        return active_runtime().corpus_status

    @app.get("/api/sample-questions")
    def sample_questions() -> dict[str, list[str]]:
        return {"questions": SAMPLE_QUESTIONS}

    @app.post("/api/ask")
    def ask(request: AskRequest) -> dict[str, Any]:
        return active_runtime().research_loop().run(request.question, evidence=request.evidence)

    def ask_stream(question: str = Query(min_length=1)) -> StreamingResponse:
        def events():
            for event in active_runtime().research_loop().stream(question):
                payload = json.dumps(event["data"], ensure_ascii=False, default=str)
                yield f"event: {event['event']}\ndata: {payload}\n\n"

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Canonical routes
    app.add_api_route("/api/ask/stream", ask_stream, methods=["GET"])
    # Compatibility aliases (older frontend called /ask/stream)
    app.add_api_route("/ask/stream", ask_stream, methods=["GET"])
    app.add_api_route("/ask", ask, methods=["POST"])

    return app


__all__ = ["AskRequest", "SAMPLE_QUESTIONS", "create_app"]
