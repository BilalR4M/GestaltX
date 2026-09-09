# AI Usage Disclosure

Honest disclosure for SLIIT Codefest 2026 Sub-track 1C. Using AI carries no penalty when tools, purposes, and human decisions are stated clearly.

## 1. Which tools we used

| Tool | Role in development |
| --- | --- |
| **Cursor** (Composer / Claude-family / Grok-family coding assistants) | Primary coding assistant: planning, draft implementations, refactors, test stubs, documentation drafts, diagram drafts |
| **Ollama** (local models, e.g. Qwen 2.5 instruct) | Runtime answer polish inside GestaltX; optional offline LLM for Answer/Why sections |
| **OpenRouter** (free-tier chat models) | Fallback provider when configured via env; not required for the demo path |
| **pytest / local eval harness** | Human-run validation of AI-generated and hand-written code (not generative tools) |

No proprietary corpus text was pasted into public web chat UIs for training. Assistants worked against the local repository checkout.

## 2. What we used them for

Across **2026-08-29 – 2026-09-09**:

- Scaffolding config, LLM client, ingest parsers, FTS/graph/tools
- Drafting the iterative research loop, gap critic, and arbitration logic
- Frontend SSE/activity feed and answer panel
- Test and documentation drafts (architecture, limitations, diagrams)
- Reconstructing reviewed chat logs for this disclosure pack after UX and corpus-watcher work

AI drafts were always treated as untrusted until reviewed, tested, and accepted by a team member.

## 3. Decisions made by the team (not by the AI)

These choices were made by human teammates and kept even when assistants suggested alternatives:

1. **Iterative research loop over one-shot RAG** — contested “wiki answers” are gaps, not final answers.
2. **Authority tiers from archive layout** — Codex (1) > wiki (2) > chronicles (3) > ephemera (4).
3. **Local-first stack** — Ollama default; dense vectors optional/skipped on CPU by default.
4. **Just-in-time section reads** — tools return compact hits; never dump whole documents into the prompt.
5. **Document the 5 Sep eval failure** — contested stall + Gloammarch 321 AS decoy recorded, then fixed with pointer follow and near-name filters.
6. **Goldens** — Gloamreach founding **246 AS**; Gauntlet forging **391 AS**; reject near-name and popular-year decoys.
7. **Impersonal, source-forward brief** — no “we/I”, no file paths in prose; LLM may polish only Answer/Why after a voice check.
8. **In-process corpus watcher** — new files must affect the next question without a manual rebuild script.
9. **Classification fallback** — root drops: filename → content → mid-trust chronicle (not silent tier-5).
10. **Submission hygiene** — never commit corpus, indexes, `.env`, or secrets; AI logs sanitized.

## 4. Chat history location

Competition requirement: export conversation logs with AI agents as **plain text (`.txt`)** in the Git repository.

Canonical logs: `ai_usage/chatlogs/*.txt`  
Index: `ai_usage/chatlogs/README.txt`

These are reviewed development-window summaries (29 Aug – 9 Sep 2026). Secrets, absolute machine paths, and raw archive quotations were removed. They outline the process; they are not a claim that every line of code was AI-authored.

## 5. Judging note

Submissions are judged on human insight, working functionality, and demonstrated understanding. GestaltX’s eval failure (5 Sep) and recovery (6 Sep), arbitration rules, and voice/dossier design are human product decisions. AI accelerated typing and exploration; the team owned architecture, validation, and the final answer.

## 6. Key hygiene (related)

No API keys appear in this disclosure or in chat-log exports. Cloud keys (if used) load from `.env` / `OPENROUTER_API_KEY` only. See `configuration-example/api-key-hygiene.md`.
