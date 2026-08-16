# Product current state v1.3 — 2026-08-14

This version preserves v1.2 and records C3 only.

## Do not reimplement

- Incident lifecycle, direct Service Request fulfillment and approval-gated Service Request lifecycle: DONE.
- Technician Service Request queue/takeover/transitions: DONE.
- Admin User Lifecycle C1: DONE.
- Technician fulfillment-group eligibility C3: DONE.
- OTel: DONE.
- AI/RAG baseline and routing/security/action grounding: FROZEN.

## C3 — technician fulfillment-group membership and eligibility

`SERVICE_POLICIES` remains the one fixed, server-owned source for fulfillment
group names and routing. `ServiceRequest.fulfillment_group` remains the
persisted route. C3 adds only `technician_fulfillment_groups`, a normalized
technician-to-canonical-group mapping with a unique technician/group constraint
and lookup indexes; there is deliberately no dynamic fulfillment-group CRUD.

The admin-only API exposes the fixed values and atomically reads/replaces a
technician's memberships. It validates the target role, duplicate and unknown
groups, writes an aggregate safe audit event, and returns authoritative state.
The Admin Users screen exposes the control only for TECHNICIAN users and shows
pending/error states; it does not claim success until the PUT succeeds.

For a normal technician, Service Request queue visibility and takeover both
require the intersection of existing tenant scope and explicit group
membership. The takeover UPDATE includes the membership predicate, so a
membership removal racing a stale takeover cannot bypass authorization. Empty
membership grants no queue visibility and no new takeover. Existing assigned
work is intentionally unaffected, so a technician removed from a group can
finish already-owned work but cannot take further work in that group.

The pre-existing ADMIN fulfillment privilege is retained as an explicit RBAC
override; group membership governs TECHNICIAN users. A TECHNICIAN role change
to another role transactionally clears memberships. A later role change back
does not restore them. The named demo `tech1` is explicitly seeded with the
catalog's current groups solely to preserve demo and existing E2E workflows;
all other existing/new technicians default to no groups.

## Evidence

- DB model/index/unique constraint: `src/models/technician_fulfillment_group.py`.
- APIs: `GET /admin/fulfillment-groups`, `GET /admin/technicians/{id}/fulfillment-groups`, `PUT /admin/technicians/{id}/fulfillment-groups`.
- Queue/takeover enforcement: `src/services/service_request_service.py`.
- Role cleanup and membership audit: `src/api/admin.py`.
- Admin UI: `/admin/users`.
- HTTP/SQLite E2E: `tests/e2e/test_technician_fulfillment_groups_v1_0.py`.

## Frozen scoring contract

The v1.2 Service Request lifecycle scoring contract is retained unchanged:

| Area | Weight | Before C3 | After C3 |
| --- | ---: | ---: | ---: |
| Direct fulfillment branch | 50 | 50 | 50 |
| Approval-gated branch | 50 | 50 | 50 |
| **Service Request lifecycle denominator** | **100** | **100%** | **100%** |

C3 is outside this denominator. Its feature status is **0% → 100%**. No
portfolio-wide completion percentage is published because there is no stable,
complete portfolio denominator.

## Remaining verified gaps

No verified P1 item remains from v1.2's source-of-truth list. Broader
unimplemented areas remain Notifications, Alerts/On-call, Manager
Change/Problem/SLA, and CMDB/organization management. The next batch should
start with a new audit that chooses one of these rather than inferring scope.
