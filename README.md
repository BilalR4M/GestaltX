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

## Team

| Member | Role |
| --- | --- |
| Bilal Awshid | Lead - agent loop, LLM, arbitration |
| Dasun Wickramasooriya | Ingestion, parsers, indexing |
| Anjana Pinnawala | Entity graph, tools, evaluation |
| Virul Methnidu Meemana | Frontend - Next.js live trace UI |

## Prerequisites

- Python 3.11+
- Node.js 20+ (frontend)
- Ollama (default) or an OpenRouter free-tier key

## Corpus (read-only)

Place the official archive at:

```text
data/raw/Ashen_Era_Archive/
```

Do not commit the corpus. Indexes are gitignored under data/processed/.

## Backend setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
pip install -e .

copy configuration-example\.env.example .env
```

Build indexes:

```bash
python scripts/build_index.py
```

Run API:

```bash
python scripts/run_api.py
```

API defaults to http://127.0.0.1:8000.

## Frontend setup

```bash
cd src/frontend
npm install
npm run dev
```

Optional src/frontend/.env.local:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Tests and evaluation

```bash
python -m pytest -q
python eval/runner.py --mode local
```

## Documentation

- docs/architecture.md
- docs/decisions.md
- docs/limitations.md
- docs/evaluation.md
- docs/submission_report.md
- ai_usage/
- configuration-example/ollama-setup.md
