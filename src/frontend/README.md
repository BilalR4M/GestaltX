# GestaltX frontend

Next.js 15 App Router interface for viewing the iterative research trace and cited answer.

## Run

```bash
cd src/frontend
npm install
```

Create `.env.local` if the API is not on the default address:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Start both the FastAPI backend and the frontend:

```bash
npm run dev
```

Open http://localhost:3000. The UI consumes `GET /ask/stream?question=...` as server-sent events named `iteration` and `answer`.
