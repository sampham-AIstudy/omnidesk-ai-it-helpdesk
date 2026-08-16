# Product current state v1.2 — 2026-08-14

This version preserves v1.1 and records C2 only.

## Do not reimplement

- Incident lifecycle: DONE.
- Direct Service Request fulfillment: DONE.
- Service Request approval lifecycle: DONE.
- Service Request tenant isolation, audit and concurrency: DONE.
- Admin User Lifecycle C1: DONE.
- OTel implementation: DONE.
- AI/RAG baseline, routing/security/action grounding: FROZEN.

## C2 — approval-gated Service Requests

Catalog approval metadata remains server-owned (`SERVICE_POLICIES.approval`).
Requests with an approval policy persist as `PENDING_APPROVAL`; direct requests
continue to persist as `SUBMITTED` and enter the existing technician queue.

A Manager/Admin in scope can approve or reject a pending request. Approval is
persisted and atomically changes it to `SUBMITTED`, deliberately reusing the
completed fulfillment queue/state machine. Rejection is terminal `REJECTED`
with a persisted required reason. Both decisions are audit logged and use CAS,
so concurrent managers have one winner and one deterministic conflict.

## Frozen completion scoring contract

This contract is limited to the **Service Request lifecycle**. It intentionally
does not reconcile v1.1's portfolio percentage, whose full denominator was not
available in the missing v1.0 artifact.

| Area | Weight | Rule | Before C2 | After C2 |
| --- | ---: | --- | ---: | ---: |
| Direct fulfillment branch | 50 | DONE earns full weight; otherwise zero | 50 | 50 |
| Approval-gated branch | 50 | DONE earns full weight; otherwise zero | 0 | 50 |
| **Service Request lifecycle denominator** | **100** | Sum of the two branches only | **50%** | **100%** |

Portfolio-wide product completion is deliberately **not reported** under this
new contract. A future whole-product audit must establish its own complete,
stable denominator before publishing a comparable percentage.

## Remaining verified P1 and C3

The remaining verified P1 gap is technician fulfillment-group membership /
eligibility administration. Today, the technician queue scopes by tenant and
can filter by `fulfillment_group`, but there is no persisted membership model;
tenant-scoped technicians are otherwise eligible. C3 should implement that
administration and no unrelated Manager, Notification, or CMDB work.
