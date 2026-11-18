# LOKI Roadmap

Each phase is its own commit or PR, so the Git history shows the project growing.

| Phase | Feature | What you learn |
|---|---|---|
| ✅ 1 | Core agent loop, file and system tools, sandbox, confirmations, push-to-talk voice | LLM tool calling, ReAct, adapters, testing with fakes |
| ✅ 2 | **Web**: search the web, read pages; untrusted-content markers, SSRF guard, context-window trimming | Web scraping, prompt injection, SSRF, context management |
| 3 | **Gmail and Calendar**: read, search, draft (send only after confirmation) | OAuth 2.0, Google APIs, least-privilege scopes |
| 4 | **Memory**: remembers facts about you and past tasks (SQLite + embeddings) | RAG, vector search, embeddings |
| 5 | **Wake word** "Hey LOKI", streaming replies | Audio streams, wake-word models (openWakeWord) |
| 6 | **Web dashboard**: chat UI, live tool log, approve/deny buttons (FastAPI + WebSocket) | Async Python, WebSockets, frontend |
| 7 | **Pluggable brains**: Claude/OpenAI adapters, model routing | Provider abstraction, cost vs quality trade-offs |
| 9 | **Browser automation** (Playwright) for sites that allow it, with confirmation before any submit | Headless browsers, DOM, ToS-aware automation |
| 8 | **Audit log and evals**: every action logged; a test set of tasks scored automatically | Observability, LLM evaluation |
