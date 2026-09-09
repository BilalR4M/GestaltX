# Export AI chat logs

Competition requirement: include conversation logs with AI agents as plain text
(`.txt`) files in the Git repository under `ai_usage/chatlogs/`.

1. Export each project chat from the assistant UI, or write a reviewed session summary.
2. Remove API keys, tokens, personal data, absolute user paths, and corpus excerpts.
3. Save as `.txt` (UTF-8) under `ai_usage/chatlogs/` with ISO-date filenames.
4. Record the model/tool used and the task outcome at the top of each file.
5. Update `ai_usage/chatlogs/README.txt` if you add a new phase log.
6. Keep `ai_usage/ai-usage-disclosure.md` aligned: tools used, for what, and
   decisions made by the team.
7. Re-run a secret scan before packaging.

The development window (29 Aug – 9 Sep 2026) is covered by the phase `.txt` logs
listed in `ai_usage/chatlogs/README.txt`.

Do not copy Cursor internal project state or private `.gestaltx/` files into the submission.
