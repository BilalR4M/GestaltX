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
