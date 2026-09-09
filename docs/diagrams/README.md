# Diagrams

Mermaid source for GestaltX architecture and runtime flows. Preview in any Mermaid-capable Markdown viewer, or paste into [mermaid.live](https://mermaid.live).

| File | Kind | Story |
| --- | --- | --- |
| [system.mmd](system.mmd) | Flowchart | Archive → indexes → loop → UI, including the watcher |
| [architecture.mmd](architecture.mmd) | Component | Client, FastAPI, processed stores, corpus |
| [research_loop.mmd](research_loop.mmd) | Flowchart | Plan, search, critique, arbitrate, synthesize |
| [answer_engine.mmd](answer_engine.mmd) | Flowchart | Dossier → heuristic brief → optional LLM polish |
| [corpus_refresh.mmd](corpus_refresh.mmd) | Flowchart | Poll / ask → diff → incremental index |
| [document_classification.mmd](document_classification.mmd) | Flowchart | Folder, filename, content, default chronicle |
| [live_answer_stream.mmd](live_answer_stream.mmd) | Sequence | SSE events and idle corpus poll |
