"""Domain-aware incident fact extraction.

This module deliberately preserves the semantic distinction between Vietnamese
``rơi`` (a physical-impact signal) and ``rồi`` (a discourse marker).  It uses
token/phrase boundaries on Unicode-normalized original text for ambiguous
physical-damage triggers; accent-folded substring matching is not safe here.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class IncidentFactProfile:
    domain: str
    required_for_workflow: tuple[str, ...]
    useful_for_diagnosis: tuple[str, ...]
    optional: tuple[str, ...]


@dataclass(frozen=True)
class IncidentFactState:
    domain: str | None
    is_incident: bool
    known_facts: dict[str, str]
    missing_required_facts: list[str]
    useful_for_diagnosis: tuple[str, ...]
    optional_facts: tuple[str, ...]


HARDWARE_PHYSICAL_DAMAGE = IncidentFactProfile(
    domain="HARDWARE_PHYSICAL_DAMAGE",
    required_for_workflow=(),
    useful_for_diagnosis=("device", "symptom", "physical_damage", "power_state"),
    optional=("asset_or_serial", "visible_damage"),
)
VPN_CONNECTIVITY = IncidentFactProfile(
    domain="VPN_CONNECTIVITY",
    required_for_workflow=(),
    useful_for_diagnosis=("vpn_symptom", "error_message", "authentication_state", "network_availability", "client_platform"),
    optional=("device",),
)
ACCOUNT_LOCKOUT = IncidentFactProfile(
    domain="ACCOUNT_LOCKOUT",
    required_for_workflow=(),
    useful_for_diagnosis=("account_state", "error_message"),
    optional=("account_identity",),
)
SOFTWARE_INCIDENT = IncidentFactProfile(
    domain="SOFTWARE_INCIDENT",
    required_for_workflow=(),
    useful_for_diagnosis=("application", "symptom", "error_message"),
    optional=("client_platform",),
)
NETWORK_INCIDENT = IncidentFactProfile(
    domain="NETWORK_INCIDENT",
    required_for_workflow=(),
    useful_for_diagnosis=("connectivity_symptom", "affected_scope", "error_message"),
    optional=("client_platform",),
)


def _normalized_original(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _has_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def _physical_impact(text: str) -> bool:
    """Use only unambiguous Vietnamese impact phrases on original Unicode."""
    markers = ("đập", "đấm", "rơi", "rớt", "va đập", "vỡ", "nứt", "làm rơi")
    return any(_has_phrase(text, marker) for marker in markers)


def _missing(profile: IncidentFactProfile, facts: dict[str, str]) -> list[str]:
    return [fact for fact in profile.required_for_workflow if fact not in facts]


def extract_incident_fact_state(question: str) -> IncidentFactState:
    """Classify an incident subtype and facts without global hardware defaults."""
    text = _normalized_original(question)
    facts: dict[str, str] = {}

    if _has_phrase(text, "vpn"):
        if any(marker in text for marker in ("không kết nối", "không vào", "lỗi", "failed", "timeout")):
            facts["vpn_symptom"] = "connection_or_authentication_failure"
        return IncidentFactState(
            VPN_CONNECTIVITY.domain, True, facts, _missing(VPN_CONNECTIVITY, facts),
            VPN_CONNECTIVITY.useful_for_diagnosis, VPN_CONNECTIVITY.optional,
        )

    if "khóa tài khoản" in text or "bị khóa" in text:
        facts["account_state"] = "locked"
        return IncidentFactState(
            ACCOUNT_LOCKOUT.domain, True, facts, _missing(ACCOUNT_LOCKOUT, facts),
            ACCOUNT_LOCKOUT.useful_for_diagnosis, ACCOUNT_LOCKOUT.optional,
        )

    hardware_signal = "laptop" in text and (
        _physical_impact(text)
        or any(marker in text for marker in ("hỏng", "lỗi", "không lên", "màn hình", "vỡ", "nứt"))
    )
    if hardware_signal:
        facts["device"] = "laptop"
        if re.search(r"màn hình\s+(?:bị\s+)?(?:tối\s+)?đen|đen xì|màn hình tối đen", text):
            facts["symptom"] = "black_screen"
        if _physical_impact(text):
            facts["physical_damage"] = "physical_impact"
            # Compatibility field retained for the existing incident triage
            # contract; it is emitted only after an unambiguous trigger.
            facts["cause"] = "physical_impact"
        if any(marker in text for marker in ("giờ", "sau khi", "xong")):
            facts["temporal_relation"] = "immediate_or_after_event"
        serial = re.search(r"(?<!\w)serial\s+([a-z0-9-]+)(?!\w)", text)
        if serial:
            facts["asset_or_serial"] = serial.group(1)
        return IncidentFactState(
            HARDWARE_PHYSICAL_DAMAGE.domain, True, facts, _missing(HARDWARE_PHYSICAL_DAMAGE, facts),
            HARDWARE_PHYSICAL_DAMAGE.useful_for_diagnosis, HARDWARE_PHYSICAL_DAMAGE.optional,
        )

    if any(marker in text for marker in ("outlook", "teams", "chrome", "phần mềm", "software")):
        return IncidentFactState(
            SOFTWARE_INCIDENT.domain, True, facts, _missing(SOFTWARE_INCIDENT, facts),
            SOFTWARE_INCIDENT.useful_for_diagnosis, SOFTWARE_INCIDENT.optional,
        )
    if any(marker in text for marker in ("wifi", "internet", "mạng", "network")):
        return IncidentFactState(
            NETWORK_INCIDENT.domain, True, facts, _missing(NETWORK_INCIDENT, facts),
            NETWORK_INCIDENT.useful_for_diagnosis, NETWORK_INCIDENT.optional,
        )
    return IncidentFactState(None, False, facts, [], (), ())
