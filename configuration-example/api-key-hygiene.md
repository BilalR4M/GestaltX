# API key hygiene and rate-limit survival

Competition rule 9.3 expectations, mapped to GestaltX.

## Keys never in Git or chats

- Load secrets from environment variables or a local `.env` file.
- `.env` and `.env.local` are listed in `.gitignore`. Do not rename a secrets file to something that is tracked.
- Copy the template only: `configuration-example/.env.example` → `.env` in the repo root.
- Put the OpenRouter key in `.env` as `OPENROUTER_API_KEY=...`. The code reads that name via `llm.openrouter_api_key_env` (default `OPENROUTER_API_KEY`).
- Never hard-code keys in source, YAML, screenshots, Discord, or AI chat exports. Judges see the full Git history — a leaked key in an old commit stays leaked.
- If a key was ever pasted or committed, revoke it in the provider dashboard and create a new one. Treat it as compromised.

Default provider is **Ollama** (no cloud key). OpenRouter is optional.

## Rate limits (HTTP 429)

Free tiers return HTTP 429 under load. GestaltX builds exponential backoff into every LLM call from day one:

- `LLMClient.chat` in `src/backend/gestaltx/llm/client.py`
- On 429: wait 1s, then 2s, 4s, 8s… (capped), up to `llm.max_retries` (default 5)
- Other transient errors also back off; connection-refused to local Ollama fails fast
- Successful responses can be cached under `.llm_cache/` (gitignored) to cut repeat calls during demos

Still expect free-tier variance during a live recording; prefer Ollama for demos when possible.

## Team quota

Rate limits are usually per account or per project. Four teammates each using their own OpenRouter (or other provider) account and key is legitimate and multiplies development quota. Do not share one key in a group chat.

## Checklist before push

```text
- [ ] No .env in the commit
- [ ] git grep / secret scan for OPENROUTER_API_KEY=sk- or similar
- [ ] Demo path works with Ollama alone (GESTALTX_LLM_PROVIDER=ollama)
```
