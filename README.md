# GestaltX

An intelligent document assistant that reads, identifies missing context, and
loops its search strategy to connect facts across complex archives.

**SLIIT Codefest 2026 - AI Competition - Sub-track 1C: Searching the Way a Human Does**

## Why not one-shot RAG

In the Ashen Era Archive, wiki articles often say a fact is contested and point
you to the Annals/Codex. Near-identical names (Gloamreach vs Gloammarch) also
poison naive retrieval. GestaltX plans a search, reads evidence into a scratchpad,
detects gaps and pointers, re-scopes the next query by authority tier, arbitrates
conflicts, and returns a cited answer with a live research trace.

The finder sees the work happen: tool cards for each archive search, collapsible
thoughts, then a brief that names the documents, attributes rival years, and
explains why the winning source stands. Drop a new file into the archive folder
and the next question includes it — no rebuild script.

## Team

| Member | Role |
| --- | --- |
| Bilal Awshid | Agent loop, LLM, arbitration |
| Dasun Wickramasooriya | Ingestion, parsers, indexing |
| Anjana Pinnawala | Entity graph, tools, evaluation |
| Virul Methnidu Meemana | Frontend - Next.js live trace UI |

## Prerequisites

- Python 3.11+
- Node.js 20+ (frontend)
- Ollama (default) or an OpenRouter free-tier key

## Corpus (read-only for the shipped archive)

Place the official archive at:

```text
data/raw/Ashen_Era_Archive/
```

Do not commit the corpus. Indexes are gitignored under `data/processed/`.

New `.md`, `.txt`, `.docx`, or `.pdf` files dropped into that folder are detected
by the API process (about every 3 seconds, and again when a question arrives).
Folder names still set authority (`codex`, `wiki`, `chronicles`, `ephemera`). A
file at the archive root is classified from its filename and headings; if that
fails it is treated as a mid-trust chronicle.

A one-time full build is only needed for a fresh checkout:

```bash
python scripts/build_index.py
```

## Backend setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
pip install -e .

copy configuration-example\.env.example .env
```

Do not put real API keys in Git, chats, or screenshots. Keys load from `.env` (gitignored). See [configuration-example/api-key-hygiene.md](configuration-example/api-key-hygiene.md). Default LLM is Ollama (no cloud key). LLM calls retry HTTP 429 with exponential backoff.

Run API:

```bash
python scripts/run_api.py
```

API defaults to http://127.0.0.1:8000.

Useful routes:

- `GET /api/health` — index ready, LLM probe, `corpus_version`
- `GET /api/corpus` — document count, watcher state, recent additions
- `GET /api/ask/stream?question=...` — live research SSE
- `POST /api/ask` — one-shot JSON answer

## Frontend setup

```bash
cd src/frontend
npm install
npm run dev
```

Optional `src/frontend/.env.local`:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Open http://localhost:3000. The left pane is the activity feed (thoughts, tool
cards, status). The right pane reveals the answer section by section.

## Tests and evaluation

```bash
python -m pytest -q
python eval/runner.py --mode local
```

Goldens: Gloamreach founding **246 AS**; Gauntlet of Sorrowfell forged **391 AS**.

## Documentation

- [docs/architecture.md](docs/architecture.md) — layers, runtime path, answer shape
- [docs/diagrams/](docs/diagrams/) — system, architecture, research loop, answer engine, corpus refresh, classification, SSE
- [docs/decisions.md](docs/decisions.md)
- [docs/limitations.md](docs/limitations.md)
- [docs/evaluation.md](docs/evaluation.md)
- [docs/submission_report.md](docs/submission_report.md)
- [ai_usage/](ai_usage/)
- [configuration-example/ollama-setup.md](configuration-example/ollama-setup.md)
- [configuration-example/api-key-hygiene.md](configuration-example/api-key-hygiene.md)
