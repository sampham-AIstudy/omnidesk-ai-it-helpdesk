# Semantic Duplicate Ticket Detection

## Flow

`Guardrail → normalize → tenant-scoped duplicate check → confirmation (when needed) → create → classify/RAG/HITL`.

The check uses the existing Chroma client and embedding backend in a ticket-only
collection. It combines vector similarity with title, service, error code,
entities, status and recency. The collection is backfilled at FastAPI startup.

## API

- `POST /api/v1/tickets/duplicate-check` previews up to three tenant-scoped matches.
- `POST /api/v1/tickets` returns `409 duplicate_confirmation_required` for a high-confidence active/resolved match unless `duplicate_decision: "create_anyway"` is supplied.
- `POST /api/v1/tickets/duplicate-action` records `resolved_existing` reuse or an explicit `false_positive` label without creating a ticket.
- `GET /api/v1/tickets/duplicate-metrics` is available to managers/admins.

Duplicate detection is advisory: it never auto-closes or rejects a ticket. When
the user creates anyway, `duplicate_of_ticket_id`, score, method and confirmer
are retained. Multiple reporters of a current issue produce a Major Incident
signal rather than a spam classification.

## Data isolation and audit

Candidates are vector-retrieved first, then filtered again by both company and
department before loading ticket details. Every detection, confirmation and
prevention decision is recorded in `audit_logs`; the metrics endpoint derives
its figures from these immutable events.

Repeated submissions are additionally protected by the project's existing
per-user sliding-window rate limiter (default: 10 submissions/minute). A limit
returns a retry response; it never auto-rejects, auto-closes or deletes a
legitimate ticket.
