GestaltX AI chat logs (development window)
==========================================

Reviewed session summaries for 2026-08-29 through 2026-09-09 (Asia/Colombo).
Competition format: plain text (.txt) as required for the Git repository submission.

Each file maps to development epics and commits on main. Secrets, absolute machine
paths, corpus quotations, and raw tool traces were removed.

INDEX
-----
2026-08-29_foundations-and-scaffold.txt
  Focus: Config, LLM client, Next.js scaffold, document models
  Contributors: Bilal, Virul, Dasun

2026-08-30_ingest-parsers-and-frontend-shell.txt
  Focus: Markdown/text parsers, ask page, commit helper
  Contributors: Dasun, Virul, Bilal

2026-08-31_metadata-chunking-and-fts.txt
  Focus: Tier metadata, chunker, FTS5 index
  Contributors: Dasun

2026-09-01-02_graph-hybrid-and-tools.txt
  Focus: Entity graph, hybrid retrieval, JIT tools
  Contributors: Anjana, Dasun

2026-09-03-04_iterative-agent-loop.txt
  Focus: Planner, gap critic, loop, arbitration
  Contributors: Bilal, Anjana, Virul

2026-09-05_first-eval-and-api-integration.txt
  Focus: FastAPI SSE, eval harness, 1c_000 failure
  Contributors: Bilal, Anjana, Virul

2026-09-06-07_pointer-recovery-and-regression.txt
  Focus: Pointer follow, near-name fix, goldens (246 AS / 391 AS)
  Contributors: Bilal, Anjana, Virul

2026-09-08_submission-docs-and-disclosure.txt
  Focus: Architecture docs, limitations, AI disclosure
  Contributors: All

2026-09-09_interactive-brief-and-corpus-watch.txt
  Focus: Live UX, voice brief, corpus watcher
  Contributors: All

HOW TO READ THESE LOGS
----------------------
Each log lists user intent, assistant action, and outcome for that slice of work.
They are reconstruction summaries for submission disclosure, not verbatim Cursor
exports. Full AI Usage Disclosure (tools, purposes, team decisions) is in:

  ai_usage/ai-usage-disclosure.md

NARRATIVE ARC
-------------
1. Build the pipeline (29 Aug - 2 Sep): ingest -> index -> graph -> tools.
2. Close the loop (3-4 Sep): plan, search, critique, arbitrate -- not one-shot RAG.
3. Fail honestly (5 Sep): eval shows contested stall + Gloammarch decoy.
4. Recover (6-7 Sep): follow pointers, disambiguate names, lock goldens.
5. Ship and polish (8-9 Sep): docs, disclosure, interactive brief, auto-index.
