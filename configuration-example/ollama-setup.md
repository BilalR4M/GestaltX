# Ollama setup

1. Install Ollama from <https://ollama.com/download>.
2. Download the default model:

   ```shell
   ollama pull qwen2.5:7b-instruct
   ```

3. Start Ollama if it is not already running:

   ```shell
   ollama serve
   ```

4. Copy `gestaltx.config.example.yaml` to `gestaltx.config.yaml` in the
   repository root. Keep `llm.provider` set to `ollama`.

GestaltX uses Ollama's OpenAI-compatible endpoint at
`http://127.0.0.1:11434/v1`. Test the installation with:

```shell
ollama run qwen2.5:7b-instruct "Reply with OK."
```

## Optional: OpenRouter

1. Copy `configuration-example/.env.example` to `.env` in the repository root (`.env` is gitignored).
2. Set `GESTALTX_LLM_PROVIDER=openrouter` and `OPENROUTER_API_KEY` in `.env` only.
3. Read [api-key-hygiene.md](api-key-hygiene.md) before using cloud keys: never commit keys, never paste them into chats, revoke immediately if leaked.
4. Free-tier HTTP 429 responses are retried with exponential backoff in `LLMClient` (1s, 2s, 4s…). Teammates may each use their own OpenRouter account to multiply quota during development.
5. Prefer Ollama for demo recordings so a cloud rate limit cannot interrupt the video.
