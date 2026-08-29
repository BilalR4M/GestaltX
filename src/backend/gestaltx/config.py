"""Configuration loader for GestaltX."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class LLMSettings(BaseModel):
    provider: Literal["ollama", "openrouter"] = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_model: str = "qwen2.5:7b-instruct"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen-2.5-7b-instruct:free"
    openrouter_api_key_env: str = "OPENROUTER_API_KEY"
    temperature: float = 0.1
    max_tokens: int = 1024
    timeout_s: float = 120.0
    max_retries: int = 5
    cache_dir: str = ".llm_cache"


class IndexSettings(BaseModel):
    fts_path: str = "data/processed/fts.sqlite3"
    qdrant_path: str = "data/processed/qdrant_local"
    collection_name: str = "ashen_chunks"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 900
    chunk_overlap: int = 120
    hybrid_fts_weight: float = 0.45
    hybrid_dense_weight: float = 0.55
    top_k: int = 8


class AgentSettings(BaseModel):
    max_iterations: int = 6
    scratchpad_token_budget: int = 3500
    enable_pointer_follow: bool = True
    enable_near_name_warnings: bool = True


class AppSettings(BaseModel):
    corpus_dir: str = "data/raw/Ashen_Era_Archive"
    processed_dir: str = "data/processed"
    documents_jsonl: str = "data/processed/documents.jsonl"
    chunks_jsonl: str = "data/processed/chunks.jsonl"
    entity_graph_path: str = "data/processed/entity_graph.json"
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


class GestaltConfig(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    index: IndexSettings = Field(default_factory=IndexSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)


class EnvSettings:
    def __init__(self) -> None:
        load_dotenv()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.gestaltx_config = os.getenv("GESTALTX_CONFIG")
        self.gestaltx_llm_provider = os.getenv("GESTALTX_LLM_PROVIDER")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: str | Path | None = None) -> GestaltConfig:
    """Load config from YAML plus environment overrides."""
    env = EnvSettings()
    cfg_path = Path(path or env.gestaltx_config or "gestaltx.config.yaml")
    example = Path("configuration-example/gestaltx.config.example.yaml")
    data: dict[str, Any] = {}
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    elif example.exists():
        data = yaml.safe_load(example.read_text(encoding="utf-8")) or {}

    if env.gestaltx_llm_provider:
        data = _deep_merge(data, {"llm": {"provider": env.gestaltx_llm_provider}})

    cfg = GestaltConfig.model_validate(data)
    if env.openrouter_api_key:
        os.environ.setdefault("OPENROUTER_API_KEY", env.openrouter_api_key)
    return cfg
