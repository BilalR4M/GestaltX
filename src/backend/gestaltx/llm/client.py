"""OpenAI-compatible LLM client with Ollama and OpenRouter providers."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from gestaltx.config import GestaltConfig, LLMSettings, load_config


class LLMClient:
    """Thin chat-completions client with disk cache and 429 backoff."""

    def __init__(self, config: GestaltConfig | None = None) -> None:
        self.config = config or load_config()
        self.settings: LLMSettings = self.config.llm
        self.cache_dir = Path(self.settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _endpoint(self) -> tuple[str, str, dict[str, str]]:
        if self.settings.provider == "openrouter":
            key = os.getenv(self.settings.openrouter_api_key_env, "")
            headers = {
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "https://github.com/BilalR4M/GestaltX",
                "X-Title": "GestaltX",
            }
            return (
                self.settings.openrouter_base_url.rstrip("/") + "/chat/completions",
                self.settings.openrouter_model,
                headers,
            )
        headers = {"Authorization": "Bearer ollama"}
        return (
            self.settings.ollama_base_url.rstrip("/") + "/chat/completions",
            self.settings.ollama_model,
            headers,
        )

    def _cache_key(self, payload: dict[str, Any]) -> Path:
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        use_cache: bool = True,
    ) -> str:
        url, model, headers = self._endpoint()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": self.settings.temperature if temperature is None else temperature,
            "max_tokens": self.settings.max_tokens if max_tokens is None else max_tokens,
        }
        cache_path = self._cache_key(payload)
        if use_cache and cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return cached["content"]

        delay = 1.0
        last_error: Exception | None = None
        for _ in range(self.settings.max_retries):
            try:
                with httpx.Client(timeout=self.settings.timeout_s) as client:
                    response = client.post(url, headers=headers, json=payload)
                if response.status_code == 429:
                    time.sleep(delay)
                    delay = min(delay * 2, 30)
                    continue
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if use_cache:
                    cache_path.write_text(
                        json.dumps({"content": content, "raw": data}, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                return content
            except Exception as exc:  # noqa: BLE001 - surface after retries
                last_error = exc
                time.sleep(delay)
                delay = min(delay * 2, 30)
        raise RuntimeError(f"LLM request failed after retries: {last_error}")


__all__ = ["LLMClient"]
