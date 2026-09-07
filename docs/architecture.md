# Architecture

GestaltX is an iterative, gap-driven research system for the Ashen Era Archive.

1. Ingestion normalizes Markdown, text, DOCX, PDF, and scanned sources into documents, sections, and chunks with source-tier metadata.
2. Indexing combines SQLite FTS5, local Qdrant vectors, and an entity graph.
3. The planner establishes the entity and claim being researched.
4. Tools search, read only relevant sections, inspect entities, list sources, and compare claims.
5. The gap critic identifies missing evidence, contested values, and documentary pointers.
6. The loop reformulates the next query until evidence is sufficient or its iteration budget is exhausted.
7. Arbitration ranks claims by source authority while preserving conflicts.
8. Synthesis returns an answer, confidence, citations, and the trace exposed through FastAPI/SSE.

The Next.js client is a presentation layer; authority decisions remain in the backend.

See `docs/diagrams/system.mmd` for the system flow.
