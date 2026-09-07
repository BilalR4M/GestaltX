# Architecture decisions

## Iterative research instead of one-shot RAG

A retrieved “contested” value is a research gap, not an answer. The loop must follow pointers and search again.

## Hybrid retrieval

FTS5 preserves exact names and dates; dense retrieval finds paraphrases; the entity graph follows archive relationships. Reranking combines their strengths.

## Authority-aware arbitration

Codex (tier 1) outranks wiki (tier 2), chronicles (tier 3), and ephemera (tier 4). A higher-tier entity-matched claim wins, but contradictory evidence remains visible.

## Just-in-time context

Tools return compact hits and load individual sections. This keeps local-model prompts within budget.

## SSE trace

Server-sent events fit a one-way research stream, work in browsers without another protocol, and let users inspect progress before synthesis.
