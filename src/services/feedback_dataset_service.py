"""Safe, offline-only feedback evidence and preference-dataset preparation.

This module deliberately has no model client, prompt optimizer, trainer, or
Chroma write path.  It stores redacted snapshots and produces only
human-review-gated candidates for a future, separately authorized workflow.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.guardrails.output_guardrails import redact_secrets_and_pii
from src.models.feedback_event import FeedbackEvent
from src.models.preference_candidate import PreferenceCandidate
from src.models.ticket_message import TicketMessage
from src.models.user import User, UserRole
from src.services.rag_service import scan_indirect_injection

EVENT_AI_RESPONSE = "AI_RESPONSE"
EVENT_TICKET_RATING = "TICKET_RATING"
EVENT_TICKET_OUTCOME = "TICKET_OUTCOME"
EVENT_HUMAN_CORRECTION = "HUMAN_CORRECTION"
PENDING_REVIEW = "PENDING_REVIEW"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"
_VALID_REVIEW_STATES = {PENDING_REVIEW, APPROVED, REJECTED}
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)\d{9,10}(?!\d)")
_EMPLOYEE_ID_RE = re.compile(r"\b(?:employee|staff|nhan\s*vien)\s*(?:id|code|ma)?\s*[:#-]?\s*[A-Z]{1,5}-?\d{3,}\b", re.IGNORECASE)

# Conservative policy for a separately approved offline experiment. These are
# deliberately not a training trigger: all conditions must pass and a human
# must still authorize a particular experiment under the evaluation contract.
DATASET_SUFFICIENCY_POLICY = {
    "policy_version": "preference-sufficiency-v2",
    "minimum_total_approved_pairs": 2_000,
    "minimum_train_pairs": 1_500,
    "minimum_validation_pairs": 200,
    "minimum_test_pairs": 200,
    "minimum_negative_examples": 600,
    "minimum_high_quality_proportion": 0.40,
    "maximum_duplicate_event_rate": 0.02,
    "maximum_privacy_rejection_rate": 0.20,
    "minimum_technical_domains": 3,
    # ``group_key`` is the deterministic ticket or conversation issue family.
    # It prevents one repeated issue from satisfying a dataset readiness gate.
    "maximum_group_concentration": 0.20,
}


@dataclass(frozen=True)
class SanitizedText:
    value: str | None
    redacted: bool = False
    discard_reason: str | None = None


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _tenant_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "unknown")


def sanitize_training_text(value: str | None, *, required: bool = False) -> SanitizedText:
    """Return redacted text or a reason why it must never enter a dataset."""
    if value is None or not str(value).strip():
        return SanitizedText(None, discard_reason="missing_required_content" if required else None)
    text = str(value).strip()
    # Keep this offline: the canonical retrieval injection scanner is purely
    # local, so unsafe ticket text is never sent to a third-party detector.
    if scan_indirect_injection(text):
        return SanitizedText(None, discard_reason="prompt_injection")
    redaction = redact_secrets_and_pii(text)
    cleaned = str(redaction.get("redacted") or "").strip()
    cleaned, email_count = _EMAIL_RE.subn("[REDACTED_EMAIL]", cleaned)
    cleaned, phone_count = _PHONE_RE.subn("[REDACTED_PHONE]", cleaned)
    cleaned, employee_count = _EMPLOYEE_ID_RE.subn("[REDACTED_EMPLOYEE_ID]", cleaned)
    if len(cleaned) < 4:
        return SanitizedText(None, discard_reason="minimum_content")
    return SanitizedText(cleaned, redacted=bool(redaction.get("issues")) or bool(email_count or phone_count or employee_count))


def _safe_sources(sources: Iterable[dict[str, Any]] | None) -> tuple[list[str], list[dict[str, str]]]:
    source_ids: list[str] = []
    citations: list[dict[str, str]] = []
    for item in sources or []:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id") or item.get("id") or item.get("label") or "").strip()
        if source_id and source_id not in source_ids:
            source_ids.append(source_id[:160])
        citation = {
            key: str(item[key])[:500]
            for key in (
                "id", "source_id", "label", "title", "domain", "kind", "source", "source_type",
                "category", "topic", "product_domain",
            )
            if item.get(key) is not None
        }
        if citation and citation not in citations:
            citations.append(citation)
    return source_ids, citations


async def _generation_event_for_message(
    db: AsyncSession,
    *,
    tenant_id: str,
    ticket_id: int,
    answer_message_id: str | None,
) -> FeedbackEvent | None:
    """Return an answer only when the caller supplies its exact message ID.

    A ticket-level rating, reopen, or technician message must never be
    silently attributed to whichever response happened to be newest.
    """
    if answer_message_id is None:
        return None
    result = await db.execute(
        select(FeedbackEvent)
        .where(
            FeedbackEvent.tenant_id == tenant_id,
            FeedbackEvent.ticket_id == ticket_id,
            FeedbackEvent.event_type == EVENT_AI_RESPONSE,
            FeedbackEvent.message_id == answer_message_id,
        )
        .limit(1)
    )
    generation = result.scalar_one_or_none()
    if generation is None:
        raise ValueError("answer_message_id must identify an AI answer in the same ticket and tenant")
    return generation


async def validate_answer_provenance(
    db: AsyncSession, *, tenant_id: str, ticket_id: int, answer_message_id: str
) -> FeedbackEvent:
    """Validate an explicit AI-answer reference without creating an event."""
    generation = await _generation_event_for_message(
        db,
        tenant_id=tenant_id,
        ticket_id=ticket_id,
        answer_message_id=answer_message_id,
    )
    assert generation is not None
    return generation


async def _append_event(
    db: AsyncSession,
    *,
    event_type: str,
    tenant_id: str,
    ticket_id: int | None = None,
    conversation_id: str | None = None,
    message_id: str | None = None,
    target_event_id: str | None = None,
    actor_role: str,
    query: str | None = None,
    answer: str | None = None,
    rating: int | None = None,
    rating_comment: str | None = None,
    ticket_outcome: str | None = None,
    outcome_reason: str | None = None,
    human_correction: str | None = None,
    sources: Iterable[dict[str, Any]] | None = None,
    model_provider: str | None = None,
    model_name: str | None = None,
    prompt_version: str | None = None,
    provenance: dict[str, Any] | None = None,
) -> FeedbackEvent:
    required = {"query": event_type == EVENT_AI_RESPONSE, "answer": event_type == EVENT_AI_RESPONSE}
    safe_values = {
        "query": sanitize_training_text(query, required=required["query"]),
        "answer": sanitize_training_text(answer, required=required["answer"]),
        "rating_comment": sanitize_training_text(rating_comment),
        "outcome_reason": sanitize_training_text(outcome_reason),
        "human_correction": sanitize_training_text(human_correction),
    }
    discard_reason = next((item.discard_reason for item in safe_values.values() if item.discard_reason), None)
    source_ids, citations = _safe_sources(sources)
    clean_provenance = dict(provenance or {})
    clean_provenance["redacted_fields"] = sorted(name for name, item in safe_values.items() if item.redacted)
    clean_provenance["event_contract_version"] = "feedback-v1"
    fingerprint = _hash({
        "event_type": event_type, "tenant_id": tenant_id, "ticket_id": ticket_id,
        "conversation_id": conversation_id, "message_id": message_id,
        "target_event_id": target_event_id, "query": safe_values["query"].value,
        "answer": safe_values["answer"].value, "rating": rating,
        "rating_comment": safe_values["rating_comment"].value,
        "ticket_outcome": ticket_outcome, "outcome_reason": safe_values["outcome_reason"].value,
        "human_correction": safe_values["human_correction"].value,
    })
    # Repeated retries must not create a second eligible training observation.
    existing = (await db.execute(select(FeedbackEvent).where(FeedbackEvent.content_hash == fingerprint))).scalar_one_or_none()
    if existing is not None:
        duplicate = FeedbackEvent(
            event_type=event_type,
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            conversation_id=conversation_id,
            message_id=message_id,
            target_event_id=target_event_id,
            actor_role=actor_role,
            retrieved_source_ids_json="[]",
            citations_json="[]",
            eligible_for_dataset=False,
            discard_reason="duplicate",
            content_hash=fingerprint,
            provenance_json=_json({
                "duplicate_of_event_id": existing.event_id,
                "event_contract_version": "feedback-v1",
            }),
        )
        db.add(duplicate)
        await db.flush()
        return duplicate
    event = FeedbackEvent(
        event_type=event_type,
        tenant_id=tenant_id,
        ticket_id=ticket_id,
        conversation_id=conversation_id,
        message_id=message_id,
        target_event_id=target_event_id,
        actor_role=actor_role,
        query_snapshot=None if discard_reason else safe_values["query"].value,
        answer_snapshot=None if discard_reason else safe_values["answer"].value,
        retrieved_source_ids_json=_json(source_ids),
        citations_json=_json(citations),
        model_provider=model_provider,
        model_name=model_name,
        prompt_version=prompt_version,
        rating=rating,
        rating_comment=None if discard_reason else safe_values["rating_comment"].value,
        ticket_outcome=ticket_outcome,
        outcome_reason=None if discard_reason else safe_values["outcome_reason"].value,
        human_correction=None if discard_reason else safe_values["human_correction"].value,
        eligible_for_dataset=discard_reason is None,
        discard_reason=discard_reason,
        content_hash=fingerprint,
        provenance_json=_json(clean_provenance),
    )
    db.add(event)
    await db.flush()
    return event


async def record_ai_response_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    ticket_id: int | None,
    conversation_id: str | None,
    message_id: str | None,
    query: str,
    answer: str,
    sources: Iterable[dict[str, Any]] | None,
    model_provider: str | None,
    model_name: str | None,
    prompt_version: str,
    provenance: dict[str, Any] | None = None,
) -> FeedbackEvent:
    return await _append_event(
        db, event_type=EVENT_AI_RESPONSE, tenant_id=tenant_id, ticket_id=ticket_id,
        conversation_id=conversation_id, message_id=message_id, actor_role="agent",
        query=query, answer=answer, sources=sources, model_provider=model_provider,
        model_name=model_name, prompt_version=prompt_version, provenance=provenance,
    )


async def record_ticket_rating_event(
    db: AsyncSession, *, tenant_id: str, ticket_id: int, rating: int, comment: str | None, actor_role: str,
    answer_message_id: str | None = None,
) -> FeedbackEvent:
    generation = await _generation_event_for_message(
        db, tenant_id=tenant_id, ticket_id=ticket_id, answer_message_id=answer_message_id,
    )
    return await _append_event(
        db, event_type=EVENT_TICKET_RATING, tenant_id=tenant_id, ticket_id=ticket_id,
        target_event_id=generation.event_id if generation else None, actor_role=actor_role,
        rating=rating, rating_comment=comment,
        provenance={"answer_linked": generation is not None, "answer_message_id": answer_message_id},
    )


async def record_ticket_outcome_event(
    db: AsyncSession, *, tenant_id: str, ticket_id: int, outcome: str, actor_role: str,
    answer_message_id: str | None = None, reason: str | None = None,
) -> FeedbackEvent:
    generation = await _generation_event_for_message(
        db, tenant_id=tenant_id, ticket_id=ticket_id, answer_message_id=answer_message_id,
    )
    return await _append_event(
        db, event_type=EVENT_TICKET_OUTCOME, tenant_id=tenant_id, ticket_id=ticket_id,
        target_event_id=generation.event_id if generation else None, actor_role=actor_role,
        ticket_outcome=outcome, outcome_reason=reason,
        provenance={"answer_linked": generation is not None, "answer_message_id": answer_message_id},
    )


async def record_human_correction_event(
    db: AsyncSession, *, tenant_id: str, ticket_id: int, message: TicketMessage, actor_role: str,
    answer_message_id: str | None = None,
) -> FeedbackEvent:
    generation = await _generation_event_for_message(
        db, tenant_id=tenant_id, ticket_id=ticket_id, answer_message_id=answer_message_id,
    )
    return await _append_event(
        db, event_type=EVENT_HUMAN_CORRECTION, tenant_id=tenant_id, ticket_id=ticket_id,
        message_id=str(message.id), target_event_id=generation.event_id if generation else None,
        actor_role=actor_role, human_correction=message.content,
        provenance={
            "answer_linked": generation is not None,
            "answer_message_id": answer_message_id,
            "correction_message_id": message.id,
        },
    )


def _event_label(events: list[FeedbackEvent]) -> tuple[str, float, list[str]]:
    evidence: list[str] = []
    ratings = [event.rating for event in events if event.rating is not None]
    outcomes = {event.ticket_outcome for event in events if event.ticket_outcome}
    has_correction = any(event.event_type == EVENT_HUMAN_CORRECTION and event.human_correction for event in events)
    if any(rating <= 2 for rating in ratings):
        evidence.append("rating_le_2")
    if "reopened" in outcomes:
        evidence.append("ticket_reopened")
    if "escalated" in outcomes:
        evidence.append("ticket_escalated")
    if has_correction:
        evidence.append("human_correction")
    if evidence:
        return "negative", 0.95 if has_correction else 0.80, evidence
    if any(rating >= 4 for rating in ratings):
        return "positive", 0.80, ["rating_ge_4"]
    if "resolved" in outcomes or "closed" in outcomes:
        # Outcome alone is useful evidence but never sufficient to build a pair.
        return "neutral", 0.35, ["resolved_without_explicit_quality_signal"]
    if any(rating == 3 for rating in ratings):
        return "neutral", 0.20, ["rating_eq_3"]
    return "neutral", 0.0, ["no_quality_signal"]


async def build_preference_candidates(db: AsyncSession, *, tenant_id: str) -> list[PreferenceCandidate]:
    """Construct only evidence-backed pairs; never invent a rejected answer."""
    events = list((await db.execute(
        select(FeedbackEvent).where(
            FeedbackEvent.tenant_id == tenant_id, FeedbackEvent.eligible_for_dataset.is_(True)
        ).order_by(FeedbackEvent.created_at, FeedbackEvent.event_id)
    )).scalars())
    generation_by_id = {event.event_id: event for event in events if event.event_type == EVENT_AI_RESPONSE}
    related: dict[str, list[FeedbackEvent]] = defaultdict(list)
    for event in events:
        if event.target_event_id in generation_by_id:
            related[event.target_event_id].append(event)
    labels = {event_id: _event_label(items) for event_id, items in related.items()}
    candidates: list[PreferenceCandidate] = []

    for event_id, items in related.items():
        generation = generation_by_id[event_id]
        label, score, evidence = labels[event_id]
        if label != "negative" or not generation.query_snapshot or not generation.answer_snapshot:
            continue
        for correction in items:
            if correction.event_type != EVENT_HUMAN_CORRECTION or not correction.human_correction:
                continue
            candidates.append(_candidate_from(
                tenant_id=tenant_id,
                group_key=f"ticket:{generation.ticket_id}" if generation.ticket_id else f"conversation:{generation.conversation_id}",
                prompt=generation.query_snapshot, chosen=correction.human_correction,
                rejected=generation.answer_snapshot, source_ids=[generation.event_id, correction.event_id],
                quality_score=max(score, 0.95), quality_tier=HIGH,
                evidence=evidence + ["corrected_human_answer"],
                metadata=_candidate_evidence_metadata(generation, items),
            ))

    # Alternative answer comparisons are deliberately restricted to one
    # ticket/conversation group, avoiding cross-ticket leakage at export time.
    by_group_prompt: dict[tuple[str, str], list[FeedbackEvent]] = defaultdict(list)
    for generation in generation_by_id.values():
        if not generation.query_snapshot or not generation.answer_snapshot or generation.event_id not in labels:
            continue
        group = f"ticket:{generation.ticket_id}" if generation.ticket_id else f"conversation:{generation.conversation_id}"
        by_group_prompt[(group, _hash(generation.query_snapshot))].append(generation)
    for (group, _prompt_hash), generations in by_group_prompt.items():
        positives = [item for item in generations if labels[item.event_id][0] == "positive"]
        negatives = [item for item in generations if labels[item.event_id][0] == "negative"]
        for chosen in positives:
            for rejected in negatives:
                if chosen.answer_snapshot == rejected.answer_snapshot:
                    continue
                candidates.append(_candidate_from(
                    tenant_id=tenant_id, group_key=group, prompt=chosen.query_snapshot or "",
                    chosen=chosen.answer_snapshot or "", rejected=rejected.answer_snapshot or "",
                    source_ids=[chosen.event_id, rejected.event_id],
                    quality_score=min(0.90, (labels[chosen.event_id][1] + labels[rejected.event_id][1]) / 2),
                    quality_tier=MEDIUM,
                    evidence=labels[chosen.event_id][2] + labels[rejected.event_id][2] + ["same_group_alternative"],
                    metadata=_candidate_evidence_metadata(chosen, related[chosen.event_id] + related[rejected.event_id]),
                ))

    persisted: list[PreferenceCandidate] = []
    for candidate in candidates:
        existing = (await db.execute(
            select(PreferenceCandidate).where(PreferenceCandidate.content_hash == candidate.content_hash)
        )).scalar_one_or_none()
        if existing is None:
            db.add(candidate)
            persisted.append(candidate)
        else:
            persisted.append(existing)
    await db.flush()
    return persisted


def _candidate_from(
    *, tenant_id: str, group_key: str, prompt: str, chosen: str, rejected: str,
    source_ids: list[str], quality_score: float, quality_tier: str, evidence: list[str],
    metadata: dict[str, Any] | None = None,
) -> PreferenceCandidate:
    if not prompt or not chosen or not rejected or chosen == rejected:
        raise ValueError("Preference candidates require distinct, evidence-backed chosen and rejected text")
    content_hash = _hash({"tenant": tenant_id, "group": group_key, "prompt": prompt, "chosen": chosen, "rejected": rejected})
    return PreferenceCandidate(
        tenant_id=tenant_id, group_key=group_key, prompt=prompt, chosen=chosen, rejected=rejected,
        source_event_ids_json=_json(source_ids),
        label_evidence_json=_json({
            "evidence": sorted(set(evidence)), "tenant_safe": True,
            "schema_version": "preference-candidate-v2", **(metadata or {}),
        }),
        quality_score=round(quality_score, 4), quality_tier=quality_tier,
        review_status=PENDING_REVIEW, content_hash=content_hash,
    )


def _candidate_evidence_metadata(generation: FeedbackEvent, events: list[FeedbackEvent]) -> dict[str, Any]:
    citations = json.loads(generation.citations_json)
    source_types = sorted({
        str(item.get("source_type") or item.get("source") or item.get("kind"))
        for item in citations if item.get("source_type") or item.get("source") or item.get("kind")
    })
    return {
        "ratings": sorted({event.rating for event in events if event.rating is not None}),
        "outcomes": sorted({event.ticket_outcome for event in events if event.ticket_outcome}),
        "source_types": source_types,
        "source_ids": json.loads(generation.retrieved_source_ids_json),
        "citations": citations,
        "technical_domains": sorted({
            str(item.get("product_domain") or item.get("topic") or item.get("category"))
            for item in citations
            if item.get("product_domain") or item.get("topic") or item.get("category")
        }),
    }


async def review_preference_candidate(
    db: AsyncSession, *, candidate_id: str, reviewer: User, status: str, note: str | None = None,
) -> PreferenceCandidate:
    if status not in {APPROVED, REJECTED}:
        raise ValueError("Review status must be APPROVED or REJECTED")
    if reviewer.role not in {UserRole.ADMIN, UserRole.MANAGER}:
        raise PermissionError("Only an administrator or manager may review a preference candidate")
    candidate = await db.get(PreferenceCandidate, candidate_id)
    if candidate is None:
        raise LookupError("Preference candidate not found")
    from src.services.auth_service import can_access_company_unit

    if not can_access_company_unit(reviewer, candidate.tenant_id):
        raise PermissionError("Reviewer cannot access this preference candidate tenant")
    if candidate.review_status != PENDING_REVIEW:
        raise ValueError("A reviewed preference candidate cannot be reviewed again")
    candidate.review_status = status
    candidate.reviewed_by_id = reviewer.id
    candidate.reviewed_at = datetime.now(UTC)
    candidate.review_note = sanitize_training_text(note).value if note else None
    await db.flush()
    return candidate


async def exclude_preference_candidate_from_training(
    db: AsyncSession, *, candidate_id: str, reason: str, excluded_by: str,
) -> PreferenceCandidate:
    """Permanently exclude one retained candidate from every training dataset.

    This deliberately does not alter ``review_status`` or source evidence. An
    exclusion is one-way: restoring a record would require a separate, audited
    retention decision instead of silently reintroducing controlled data.
    """
    normalized_reason = reason.strip()
    normalized_actor = excluded_by.strip()
    if not normalized_reason or not normalized_actor:
        raise ValueError("Training exclusion requires a reason and actor")
    candidate = await db.get(PreferenceCandidate, candidate_id)
    if candidate is None:
        raise LookupError("Preference candidate not found")
    if candidate.excluded_from_training:
        if (
            candidate.training_exclusion_reason != normalized_reason
            or candidate.training_excluded_by != normalized_actor
        ):
            raise ValueError("Preference candidate is already excluded with different audit metadata")
        return candidate
    candidate.excluded_from_training = True
    candidate.training_exclusion_reason = normalized_reason[:160]
    candidate.training_excluded_by = normalized_actor[:80]
    candidate.training_excluded_at = datetime.now(UTC)
    await db.flush()
    return candidate


def deterministic_split(group_key: str) -> str:
    bucket = int(hashlib.sha256(group_key.encode("utf-8")).hexdigest()[:8], 16) % 100
    return "train" if bucket < 80 else ("validation" if bucket < 90 else "test")


async def export_approved_preference_dataset(
    db: AsyncSession, *, tenant_id: str, output_dir: Path, dataset_version: str = "feedback-preference-v1",
) -> dict[str, int]:
    """Export review-approved, non-low-risk pairs for exactly one tenant."""
    approved = list((await db.execute(
        select(PreferenceCandidate).where(
            PreferenceCandidate.tenant_id == tenant_id,
            PreferenceCandidate.review_status == APPROVED,
            PreferenceCandidate.quality_tier.in_((HIGH, MEDIUM)),
            PreferenceCandidate.excluded_from_training.is_(False),
        ).order_by(PreferenceCandidate.candidate_id)
    )).scalars())
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    seen_hashes: set[str] = set()
    for item in approved:
        if item.content_hash in seen_hashes:
            continue
        seen_hashes.add(item.content_hash)
        split = deterministic_split(item.group_key)
        evidence = json.loads(item.label_evidence_json)
        rows[split].append({
            "prompt": item.prompt,
            "chosen": item.chosen,
            "rejected": item.rejected,
            "metadata": {
                "source_event_ids": json.loads(item.source_event_ids_json),
                "tenant_safe": True,
                "quality_score": item.quality_score,
                "quality_tier": item.quality_tier,
                "review_status": item.review_status,
                "reviewer_decision": {
                    "reviewed_by_id": item.reviewed_by_id,
                    "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
                },
                "schema_version": "preference-dataset-v1",
                "dataset_version": dataset_version,
                "group_key": item.group_key,
                "split": split,
                "evidence": evidence.get("evidence", []),
            },
        })
    for split, values in rows.items():
        (output_dir / f"{split}.jsonl").write_text(
            "".join(_json(row) + "\n" for row in values), encoding="utf-8"
        )
    all_rows = [row for values in rows.values() for row in values]
    source_event_ids = {
        event_id for row in all_rows for event_id in row["metadata"]["source_event_ids"]
    }
    (output_dir / "manifest.json").write_text(_json({
        "dataset_version": dataset_version,
        "schema_version": "preference-dataset-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "record_count": len(all_rows),
        "train_count": len(rows["train"]),
        "validation_count": len(rows["validation"]),
        "test_count": len(rows["test"]),
        "content_hash": _hash(all_rows),
        "source_event_count": len(source_event_ids),
        "approval_policy_version": "approved-high-medium-v1",
        "tenant_id": tenant_id,
    }) + "\n", encoding="utf-8")
    return {name: len(values) for name, values in rows.items()}


async def dataset_quality_report(db: AsyncSession, *, tenant_id: str) -> dict[str, Any]:
    events = list((await db.execute(select(FeedbackEvent).where(FeedbackEvent.tenant_id == tenant_id))).scalars())
    candidates = list((await db.execute(select(PreferenceCandidate).where(PreferenceCandidate.tenant_id == tenant_id))).scalars())
    eligible_candidates = [item for item in candidates if not item.excluded_from_training]
    ratings = Counter(str(event.rating) for event in events if event.rating is not None)
    outcomes = Counter(event.ticket_outcome for event in events if event.ticket_outcome)
    discarded = Counter(event.discard_reason for event in events if not event.eligible_for_dataset)
    statuses = Counter(candidate.review_status for candidate in eligible_candidates)
    split_sizes = Counter(deterministic_split(candidate.group_key) for candidate in eligible_candidates if candidate.review_status == APPROVED)
    return {
        "total_feedback_events": len(events),
        "qualified_events": sum(event.eligible_for_dataset for event in events),
        "discarded_events": sum(not event.eligible_for_dataset for event in events),
        "discard_reasons": dict(sorted(discarded.items())),
        "preference_candidates": len(eligible_candidates),
        "total_preference_candidates": len(candidates),
        "excluded_from_training": len(candidates) - len(eligible_candidates),
        "approved_pairs": statuses[APPROVED],
        "rejected_pairs": statuses[REJECTED],
        "pending_pairs": statuses[PENDING_REVIEW],
        "pii_filtered_events": sum(bool(json.loads(event.provenance_json).get("redacted_fields")) for event in events),
        "injection_rejected_events": discarded["prompt_injection"],
        "duplicate_events": discarded["duplicate"],
        "rating_distribution": dict(sorted(ratings.items())),
        "outcome_distribution": dict(sorted(outcomes.items())),
        "train_validation_test_sizes": {name: split_sizes[name] for name in ("train", "validation", "test")},
    }


def _normalized_pair_key(candidate: PreferenceCandidate) -> str:
    """Cheap, deterministic near-duplicate diagnostic; it never changes data."""
    def normalize(text: str) -> str:
        return re.sub(r"\W+", " ", text.casefold()).strip()

    return _hash({
        "prompt": normalize(candidate.prompt),
        "chosen": normalize(candidate.chosen),
        "rejected": normalize(candidate.rejected),
    })


async def dataset_readiness_report(
    db: AsyncSession, *, tenant_id: str | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read-only counts and conservative DPO/ORPO data-sufficiency decision."""
    active_policy = dict(DATASET_SUFFICIENCY_POLICY if policy is None else policy)
    event_stmt = select(FeedbackEvent)
    candidate_stmt = select(PreferenceCandidate)
    if tenant_id is not None:
        event_stmt = event_stmt.where(FeedbackEvent.tenant_id == tenant_id)
        candidate_stmt = candidate_stmt.where(PreferenceCandidate.tenant_id == tenant_id)
    events = list((await db.execute(event_stmt)).scalars())
    candidates = list((await db.execute(candidate_stmt)).scalars())
    eligible_candidates = [item for item in candidates if not item.excluded_from_training]
    approved = [
        item for item in eligible_candidates
        if item.review_status == APPROVED and item.quality_tier in {HIGH, MEDIUM}
    ]
    split_counts = Counter(deterministic_split(item.group_key) for item in approved)
    tiers = Counter(item.quality_tier for item in eligible_candidates)
    statuses = Counter(item.review_status for item in eligible_candidates)
    ratings = Counter(str(item.rating) for item in events if item.rating is not None)
    signal_sources: Counter[str] = Counter()
    technical_domains: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()
    normalized_pair_counts: Counter[str] = Counter()
    unique_approved: list[PreferenceCandidate] = []
    for item in approved:
        pair_key = _normalized_pair_key(item)
        normalized_pair_counts[pair_key] += 1
        # Exact/normalized duplicate pairs cannot increase either numerator or
        # denominator for the diversity check.
        if normalized_pair_counts[pair_key] > 1:
            continue
        unique_approved.append(item)
        group_counts[item.group_key] += 1
        evidence = json.loads(item.label_evidence_json)
        signal_sources.update(evidence.get("evidence", []))
        technical_domains.update(evidence.get("technical_domains", []))
    duplicate_events = sum(event.discard_reason == "duplicate" for event in events)
    privacy_rejected = sum(
        event.discard_reason in {"prompt_injection", "minimum_content", "missing_required_content"}
        or bool(json.loads(event.provenance_json).get("redacted_fields"))
        for event in events
    )
    event_total = len(events)
    duplicate_event_rate = duplicate_events / event_total if event_total else 0.0
    privacy_rejection_rate = privacy_rejected / event_total if event_total else 0.0
    high_proportion = tiers[HIGH] / len(approved) if approved else 0.0
    largest_group, largest_group_count = max(group_counts.items(), key=lambda item: item[1], default=(None, 0))
    max_group_proportion = largest_group_count / len(unique_approved) if unique_approved else 0.0
    near_duplicate_pairs = sum(count - 1 for count in normalized_pair_counts.values() if count > 1)
    reasons: list[str] = []
    checks = {
        "minimum_total_approved_pairs": len(approved) >= active_policy["minimum_total_approved_pairs"],
        "minimum_train_pairs": split_counts["train"] >= active_policy["minimum_train_pairs"],
        "minimum_validation_pairs": split_counts["validation"] >= active_policy["minimum_validation_pairs"],
        "minimum_test_pairs": split_counts["test"] >= active_policy["minimum_test_pairs"],
        "minimum_negative_examples": len(approved) >= active_policy["minimum_negative_examples"],
        "minimum_high_quality_proportion": high_proportion >= active_policy["minimum_high_quality_proportion"],
        "maximum_duplicate_event_rate": duplicate_event_rate <= active_policy["maximum_duplicate_event_rate"],
        "maximum_privacy_rejection_rate": privacy_rejection_rate <= active_policy["maximum_privacy_rejection_rate"],
        "minimum_technical_domains": len(technical_domains) >= active_policy["minimum_technical_domains"],
        "maximum_group_concentration": bool(unique_approved)
        and max_group_proportion <= active_policy["maximum_group_concentration"],
    }
    for name, passed in checks.items():
        if not passed:
            reasons.append(name)
    if tenant_id is None:
        reasons.insert(0, "tenant_scope_required_for_training_dataset")
    if not approved:
        reasons.insert(0, "no_approved_real_preference_pairs")
    ready = not reasons
    return {
        "scope": {"tenant_id": tenant_id, "tenant_safe": tenant_id is not None},
        "policy": active_policy,
        "feedback_events": event_total,
        "qualified_events": sum(event.eligible_for_dataset for event in events),
        "preference_candidates": len(eligible_candidates),
        "total_preference_candidates": len(candidates),
        "excluded_from_training": len(candidates) - len(eligible_candidates),
        "review_status": {state: statuses[state] for state in (PENDING_REVIEW, APPROVED, REJECTED)},
        "quality_tier": {tier: tiers[tier] for tier in (HIGH, MEDIUM, LOW)},
        "split": {name: split_counts[name] for name in ("train", "validation", "test")},
        "duplicate_event_rate": round(duplicate_event_rate, 6),
        "near_duplicate_pair_count": near_duplicate_pairs,
        "pii_rejection_count": privacy_rejected,
        "injection_rejection_count": sum(event.discard_reason == "prompt_injection" for event in events),
        "rating_distribution": dict(sorted(ratings.items())),
        "signal_source_distribution": dict(sorted(signal_sources.items())),
        "technical_domain_distribution": dict(sorted(technical_domains.items())),
        "high_quality_proportion": round(high_proportion, 6),
        "group_concentration": {
            "grouping_dimension": "ticket_or_conversation_issue_family",
            "largest_group": largest_group,
            "largest_group_count": largest_group_count,
            "largest_group_ratio": round(max_group_proportion, 6),
            "maximum_allowed": active_policy["maximum_group_concentration"],
            "group_concentration_check": checks["maximum_group_concentration"],
            "unique_approved_pairs": len(unique_approved),
        },
        "checks": checks,
        "DPO_DATA_READY": ready,
        "ORPO_DATA_READY": ready,
        "reasons": reasons,
    }
