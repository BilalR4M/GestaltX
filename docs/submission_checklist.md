# Submission checklist

- [ ] Place the unmodified archive at `data/raw/Ashen_Era_Archive/`
- [ ] Install Python and frontend dependencies
- [ ] Build the normalized corpus and hybrid indexes once (`python scripts/build_index.py`)
- [ ] Run the backend and verify `/docs`, `/api/health`, and `/api/corpus` (`watching: true`)
- [ ] Run the frontend and complete a streamed query; confirm tool cards and five answer sections
- [ ] Drop a test `.md` into the archive root, wait a few seconds, confirm `/api/corpus` version increments
- [ ] Run `python -m pytest -q`
- [ ] Run local and HTTP evaluation modes
- [ ] Confirm `1c_000` returns 246 AS with a Codex citation
- [ ] Verify no corpus, cache, index, `.env`, or secret is committed
- [ ] Export and review AI chat logs under `ai_usage/chatlogs/`
- [ ] Review AI-use disclosure and limitations
- [ ] Package source, documentation, diagrams, and reproducible setup instructions
