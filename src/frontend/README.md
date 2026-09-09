# GestaltX frontend

Next.js 15 App Router interface for the live research activity feed and the cited brief.

## Run

```bash
cd src/frontend
npm install
```

Create `.env.local` if the API is not on the default address:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Start the FastAPI backend, then:

```bash
npm run dev
```

Open http://localhost:3000.

## What the UI consumes

`GET /api/ask/stream?question=...` as server-sent events:

| Event | Use |
| --- | --- |
| `activity` | Tool cards (`tool_start` / `tool_end`) and status pills (including corpus refresh) |
| `reasoning` | Collapsible thought steps |
| `answer_chunk` | Progressive Answer / Documents / Why / How / Sources |
| `answer` | Final brief, confidence, citations |
| `iteration` | Legacy fallback if older backends omit `reasoning` |

While idle the page polls `GET /api/corpus` every 4 seconds. A rising `version` shows an “Archive updated” chip with the new document title and kind.
