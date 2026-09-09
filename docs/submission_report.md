# GestaltX submission report

GestaltX demonstrates “searching the way a human does” by turning uncertainty into another research step. It combines hybrid retrieval, documentary pointer following, near-name entity checks, source-tier arbitration, and cited synthesis.

The principal demonstration uses a wiki entry that marks Gloamreach's founding as contested. GestaltX follows the authority trail to the Codex, distinguishes Gloamreach from Gloammarch, and answers **246 AS** with evidence rather than copying the 321 AS decoy.

The finder does not receive a keyword dump. The live trace shows each archive search as a tool card and each judgment as a short thought. The written brief names documents in ordinary language, attributes conflicting years, and states why the official source stands. Adding a new file to the archive folder is enough for the next question to consider it.

The deliverable includes a FastAPI backend, a Next.js activity-feed interface, an incremental corpus watcher, an offline evaluation harness, regression tests, architecture notes with flow diagrams, limitations, and AI-use disclosure.

## AI Usage Disclosure (summary)

Full disclosure: [ai_usage/ai-usage-disclosure.md](../ai_usage/ai-usage-disclosure.md).

**Tools:** Cursor coding assistants (Composer / Claude / Grok-family); Ollama (local) and optional OpenRouter for runtime answer polish.

**Used for:** Draft implementations, planning, tests, documentation, and reviewed chat-log summaries across 29 Aug – 9 Sep 2026. All AI output was reviewed and tested by the team before acceptance.

**Team decisions (human):** iterative loop over one-shot RAG; authority tiers; local-first stack; JIT retrieval; honest documentation of the 5 Sep eval failure; goldens 246 AS / 391 AS; impersonal source-forward brief; in-process corpus watcher; never commit corpus/secrets.

**Chat history:** plain-text logs in [ai_usage/chatlogs/](../ai_usage/chatlogs/README.txt) (`.txt` files as required for submission).
