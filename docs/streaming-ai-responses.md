# Streaming AI responses

The Help Desk exposes Server-Sent Events (SSE) for low-latency AI output:

- `POST /api/v1/chat/stream` streams the Copilot answer after ACL-scoped RAG and optional web-research preparation.
- `POST /api/v1/tickets/{ticket_id}/messages/stream` streams the AI response inside a ticket conversation; the final message is persisted once the stream completes.

The client receives `meta`, `token`, `replace`, and `done` events. `done` is the
security-filtered authoritative response. A short output buffer prevents
incomplete Markdown or credential patterns from being painted while the model is
still generating.

Internal KB references are returned as in-product `/employee/kb?search=...`
links. External sources remain new-tab links and are only shown when retrieval
returned their actual URL.
