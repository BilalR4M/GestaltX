# Architecture decisions

## Iterative research instead of one-shot RAG

A retrieved “contested” value is a research gap, not an answer. The loop must follow pointers and search again.

## Hybrid retrieval

FTS5 preserves exact names and dates; dense retrieval finds paraphrases; the entity graph follows archive relationships. Reranking combines their strengths. Dense vectors stay optional because a full FastEmbed pass over the archive is slow on CPU; FTS plus the graph are enough for the 1C goldens.

## Authority-aware arbitration

Codex (tier 1) outranks wiki (tier 2), chronicles (tier 3), and ephemera (tier 4). A higher-tier entity-matched claim wins, but contradictory evidence remains visible in the dossier.

## Just-in-time context

Tools return compact hits and load individual sections. This keeps local-model prompts within budget.

## SSE activity feed

Server-sent events fit a one-way research stream. Named events (`reasoning`, `activity`, `answer_chunk`, `answer`) let the UI show tool cards and progressive sections without another protocol.

## Impersonal, source-forward voice

The finder is not a developer. Answers never say “we”, never print file paths in prose, and must attribute rival years to named documents. A validator (`gestaltx.agent.voice`) rejects slop; the LLM may polish only Answer and Why, and only after that check.

## Incremental corpus watch instead of a rebuild script

New files must influence the next answer without `scripts/build_index.py`. A manifest of path / size / mtime drives incremental FTS replace, JSONL merge, and a full graph rebuild (near-name warnings need a global pass). The question path blocks on a refresh lock so a drop one second earlier is not missed.

## Classification fallback for root drops

Folder family is still the authority signal. A file outside `codex` / `wiki` / `chronicles` / `ephemera` is inferred from filename keywords, then content headings, then defaults to tier 3 chronicle so it is competitive but not official.

## 2026-09-06 recovery

After the 5 Sep eval failed on 1c_000 (contested stall + Gloammarch decoy), pointer-following to Codex/Annals and near-name warnings were enabled. Gloamreach founding resolves to **246 AS**; Gauntlet forging resolves to **391 AS**.

## 2026-09-09 interactive brief and live archive

The UI and synthesis were rewritten so the research path is visible and the verdict is a human brief. The API process now watches the corpus so added documents are indexed automatically.
