# AI usage disclosure

Generative AI assisted with planning, implementation drafts, test design, documentation, diagrams, and code review for GestaltX. Human team members remain responsible for architecture choices, validation, integration, source handling, and the submitted result.

On 2026-09-09, Cursor (Composer / Grok-family coding assistants) was used to:

- implement the live activity-feed UI and structured answer sections
- rewrite synthesis into an impersonal, source-forward brief with a voice validator
- add the in-process corpus watcher so new archive files are indexed without a rebuild script
- update architecture documentation and flow diagrams
- produce reviewed chat logs in `ai_usage/chatlogs/`

AI output was treated as untrusted: claims were checked against repository evidence, generated code was reviewed and tested, and unavailable competition data was marked missing rather than invented. No archive corpus or secrets are intentionally included in chat-log exports.
