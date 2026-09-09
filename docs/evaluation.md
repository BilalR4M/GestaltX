# Evaluation

Run locally after indexing:

```bash
python eval/runner.py --mode local
```

Or evaluate the running API:

```bash
python eval/runner.py --mode http --api-url http://127.0.0.1:8000
```

The runner compares available answers with `eval/golden/1c_answers.json` and writes Markdown reports. Missing official prompts are explicitly skipped. The key regression is `1c_000`: Gloamreach must resolve to **246 AS**, while Gloammarch's **321 AS** is rejected as an entity mismatch.

Unit coverage that guards the 9 Sep work:

- `tests/test_voice.py` — no we/I/path slop; rival years attributed
- `tests/test_corpus_watch.py` — add / modify / delete refresh; root `codex_of_x.md` is tier 1; `random_notes.md` is tier 3
- `tests/test_1c_golden.py` — 246 AS and 391 AS

Historical reports document the initial failure and subsequent recovery.
