# Chat log — interactive brief, live trace, corpus watch

- **Date:** 2026-09-09 (Asia/Colombo)
- **Tool:** Cursor coding assistant (Composer / Grok-family)
- **Scope:** This project chat, from structured-answer work through automatic corpus recognition and documentation
- **Reviewed:** Yes. Screenshots, absolute machine paths, corpus quotations, and secrets removed. Tool traces condensed. Internal plan-file names omitted.

## Outcome

The product now streams a live research feed, writes a five-section human brief with voice checks, and indexes new archive files inside the API process. Goldens remain 246 AS (Gloamreach founding) and 391 AS (Gauntlet of Sorrowfell). Tests: 18 passed at the end of the watcher work.

## Turns (reviewed)

### Structured answers for an interactive assistant

**User:** The page showed no useful response. They wanted an LLM-backed, properly structured reply to the search prompt, working as an interactive AI.

**Assistant:** Wired synthesis to emit a structured Markdown brief (direct answer, supporting context, citations) over SSE, and made the answer panel parse those sections. When Ollama was offline the loop fell back to a heuristic brief so the UI still answered.

**User:** The fact was correct, but the finder needed relevant information *below* the answer so the verdict made sense.

**Assistant:** Added a context section under the verdict: what other sources said, and why the Codex year was kept.

### Human chain of thought

**User:** The detailing did not look like human thinking. Humans show a clear chain of thought. Plan the whole look of the system and the output quality.

**Assistant (plan, then implement):** Introduced streamed `reasoning` events (plan → finding → judgment) and a left-pane thought list. The right pane kept the structured verdict. Narrator copy was still too internal (“we will search…”, “tier 1”).

### Live agentic UX

**User:** Improve the wording so a non-technical reader can follow it. Visualize searching live, in the style of current agentic UIs (tool calls with spinners, not a static log).

**Assistant (plan, then implement):**

- Backend: `activity` events (`tool_start`, `tool_end`, `status`) and `answer_chunk` for progressive sections.
- Frontend: tool cards with query + hit count, collapsible older thoughts, a working card on the answer side, then sections revealing in order.
- Shared LLM probe so `/api/health` and the loop agree on whether Ollama is up.

### Voice and transparency

**User:** Find the flaws: AI slop, redundancy, overuse of “we”. Want a clear, non-technical response that shows which documents were found and why the answer was chosen.

**Assistant (plan, then implement):**

- Document dossier: friendly titles, kinds (official codex / community wiki / chronicle / loose paper), locators, roles (settles / disputes / pointer / mentions).
- Answer shape: Answer, What the documents say, Why this is the answer, How this answer was found, Sources.
- `voice.py` bans pronouns, slop phrases, and file-path artifacts. LLM may rewrite only Answer and Why from a compact dossier; failed checks keep the heuristic text.
- Confidence labels and a short note instead of a silent 0.85 bump for any tier-1 hit.

### Automatic corpus recognition

**User:** If any new document is added to the corpus, the agent should notice it and use it, seamlessly, without running scripts.

**Assistant (plan, then implement):**

- Manifest-driven `CorpusWatcher` in the API process (poll ~3s, plus a pre-query staleness check).
- Incremental parse/chunk; FTS `remove_document` + add; JSONL merge; full entity-graph rebuild; `runtime.invalidate()`.
- Classification: folder first, then filename keywords, then content headings, else tier-3 chronicle.
- `GET /api/corpus`; health includes `corpus_version`; UI chip when version rises; research feed status when a refresh happened mid-ask.

**Follow-up in the same chat:** An API restart hung because first boot tried to re-parse the whole archive when the manifest was missing. Startup now seeds the manifest from existing JSONL. Health after restart: index ready, watching true, 255 documents.

### Documentation (this turn)

**User:** Update documentation with the new work, add flow and architecture diagrams, and write reviewed chat logs as Markdown under the AI usage folder.

**Assistant:** Updated README, architecture, decisions, limitations, evaluation, submission notes, and frontend README. Added Mermaid diagrams for system, components, research loop, answer engine, corpus refresh, classification, and SSE. Wrote this reviewed log and refreshed the AI-usage disclosure.

## What was not copied here

- Full assistant tool traces and code diffs
- UI screenshots
- Raw archive text
- Local paths, process IDs, and API keys
- Private `.gestaltx/` playbook contents
