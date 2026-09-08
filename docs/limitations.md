# Limitations

- OCR is brittle on degraded scans, unusual typefaces, marginalia, and multi-column pages.
- Free OpenRouter models have variable availability and rate limits; retries and caching reduce but do not remove this risk.
- Local small models may mishandle subtle contradictions or produce malformed tool arguments.
- One-shot RAG is not reliable for contested claims, documentary pointers, or near-name decoys.
- Authority tiers encode archive conventions and cannot prove that a source is historically true.
- Confidence is an evidence-quality indicator, not a calibrated probability.
- The official sample-question artifact and corpus are not distributed in this workspace, so unavailable eval prompts are skipped rather than fabricated.
