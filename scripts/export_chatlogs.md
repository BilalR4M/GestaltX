# Export AI chat logs

1. Export each project chat from the assistant UI as plain text.
2. Remove API keys, tokens, personal data, absolute user paths, and corpus excerpts not allowed in the submission.
3. Save the reviewed files under `ai_usage/chatlogs/` with ISO-date filenames.
4. Record the model/tool used and the task outcome at the top of each file.
5. Re-run a secret scan before packaging.

Do not copy Cursor's internal project state or private `.gestaltx/` files into the submission.
