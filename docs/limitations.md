# Limitations

- OCR is brittle on degraded scans, unusual typefaces, marginalia, and multi-column pages.
- Free OpenRouter models have variable availability and rate limits; `LLMClient` retries HTTP 429 with exponential backoff (1s, 2s, 4s…) and caches successful replies under `.llm_cache/`. Prefer Ollama for demos. See `configuration-example/api-key-hygiene.md`.
- Local small models may mishandle subtle contradictions. GestaltX therefore treats the LLM as optional polish on Answer and Why; the heuristic brief is the source of truth when Ollama is offline or voice validation fails.
- One-shot RAG is not reliable for contested claims, documentary pointers, or near-name decoys.
- Authority tiers encode archive conventions and cannot prove that a source is historically true.
- Confidence is an evidence-quality indicator, not a calibrated probability.
- Dense vector indexing is skipped by default. New documents are added to FTS and the entity graph only unless `GESTALTX_USE_DENSE=1` and a Qdrant store already exists.
- The watcher debounce (about 1.5s) can delay a file that is still being copied. The next poll or the next question picks it up.
- Files dropped at the archive root without a recognizable name or heading become mid-trust chronicles. Move official material into `codex/` if it must outrank the wiki.
- The official sample-question artifact and corpus are not distributed in this workspace, so unavailable eval prompts are skipped rather than fabricated.
