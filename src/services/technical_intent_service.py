"""Deterministic technical intent facets for bounded retrieval compatibility.

This module intentionally derives only compact technical primitives.  It does
not persist query text, call an LLM, or contain evaluation identifiers.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return "".join(char for char in normalized if not unicodedata.combining(char)).replace("đ", "d")


@dataclass(frozen=True)
class TechnicalFacets:
    protocol: str = "unknown"
    network_layer: str = "unknown"
    port: int | None = None
    http_status: int | None = None
    connection_symptom: str = "unknown"
    vpn_stage: str = "unknown"
    network_area: str = "unknown"
    predicted_topic: str = "unknown"

    def public_dict(self) -> dict[str, Any]:
        """Return only derived facets; raw user query is never included."""
        return asdict(self)


_PORT_NUMBER = re.compile(r"\b(?:port|cong|tcp|udp)\s*(?:number\s*)?(\d{1,5})\b")


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)


def infer_technical_facets(query: str) -> TechnicalFacets:
    """Compose general technical primitives into a compact diagnostic intent."""
    text = _fold(query)
    has_http_marker = _has_any(text, ("http", "https", "api", "browser", "web", "website", "forbidden"))
    http_codes = [int(value) for value in re.findall(r"\b(401|403|404|500|502)\b", text)]
    port_match = _PORT_NUMBER.search(text)
    explicit_raw_port = port_match is not None and bool(
        re.search(r"\b(?:not|khong(?:\s+phai)?|no)\s+(?:a\s+)?http\b", text)
    )
    http_status = (
        403 if has_http_marker and "forbidden" in text else (http_codes[-1] if has_http_marker and http_codes else None)
    )
    if explicit_raw_port:
        http_status = None
    port = int(port_match.group(1)) if port_match else None

    has_tcp = _has_any(text, ("tcp", "udp", "port", "cong", "test-netconnection", "tcptestsucceeded"))
    has_ping = _has_any(text, ("ping", "icmp"))
    if has_ping and re.search(r"\b\d{2,5}\b", text):
        has_tcp = True
    has_timeout = _has_any(text, ("timeout", "timed out", "time out"))
    has_refused = _has_any(text, ("refused", "tu choi", "reject", "rejected"))
    has_reset = _has_any(text, ("reset", "rst"))
    has_listener = _has_any(text, ("listener", "listening", "listen", "lang nghe"))
    has_vpn = _has_any(text, ("vpn", "forticlient", "ssl-vpn", "ssl vpn"))
    has_login = _has_any(text, ("login", "dang nhap", "authentication", "auth", "certificate", "profile", "mfa"))
    has_connected = _has_any(text, ("connected", "ket noi", "len roi", "vao roi", "tunnel"))
    has_internal = _has_any(text, ("internal", "noi bo", "intranet", "server", "app unreachable", "khong vao"))

    if http_status is not None:
        protocol, network_layer = ("https" if "https" in text else "http"), "application"
    elif has_tcp:
        protocol, network_layer = "udp" if "udp" in text and "tcp" not in text else "tcp", "l4"
    elif has_ping:
        protocol, network_layer = "unknown", "l3"
    else:
        protocol, network_layer = "unknown", "unknown"

    if has_listener:
        symptom = "service_not_listening"
    elif has_refused:
        symptom = "refused"
    elif has_timeout:
        symptom = "timeout"
    elif has_reset:
        symptom = "reset"
    else:
        symptom = "unknown"

    if has_vpn and has_login:
        vpn_stage = "authentication"
    elif has_vpn and has_connected and has_internal:
        vpn_stage = "post_connection"
    elif has_vpn and has_connected:
        vpn_stage = "tunnel_establishment"
    else:
        vpn_stage = "unknown"

    if _has_any(text, ("dns", "resolve-dnsname", "resolve", "hostname", "name resolution")):
        area = "dns"
    elif _has_any(text, ("proxy", "reverse proxy")):
        area = "proxy"
    elif _has_any(text, ("route", "routing", "dinh tuyen", "split tunnel", "subnet", "interface")):
        area = "routing"
    elif _has_any(text, ("firewall", "acl", "nat")):
        area = "firewall"
    elif has_vpn:
        area = "vpn"
    else:
        area = "generic"

    if http_status is not None:
        predicted = "http.status_403" if http_status == 403 else "http.application"
    elif has_ping and has_tcp:
        predicted = "network.tcp_connectivity"
    elif vpn_stage == "authentication":
        predicted = "vpn.forticlient_auth"
    elif vpn_stage == "post_connection":
        predicted = "vpn.internal_resource_access"
    elif area == "dns":
        predicted = "dns"
    elif area == "routing":
        predicted = "routing"
    elif area == "proxy":
        predicted = "proxy"
    elif symptom == "service_not_listening":
        predicted = "network.service_not_listening"
    elif symptom == "refused":
        predicted = "network.connection_refused"
    elif port is not None:
        predicted = "network.port_connectivity"
    elif symptom == "timeout":
        predicted = "network.port_timeout"
    elif has_tcp:
        predicted = "network.port_connectivity"
    else:
        predicted = "unknown"

    return TechnicalFacets(protocol, network_layer, port, http_status, symptom, vpn_stage, area, predicted)


_TOPIC_ALIASES = {
    "network.l3_vs_l4": "network.tcp_connectivity",
    "network.tcp.timeout_refused_reset": "network.tcp_failure_semantics",
    "network.port_connectivity": "network.port_connectivity",
    "network.service_not_listening": "network.service_not_listening",
    "network.firewall_acl_nat": "network.firewall_acl",
    "vpn.forticlient.ssl_vpn": "vpn.forticlient_auth",
    "vpn.connected_internal_unreachable": "vpn.internal_resource_access",
    "network.routing_split_tunnel": "routing",
    "network.dns_proxy": "dns_proxy",
    "http.status_403": "http.status_403",
}


def topic_compatibility(facets: TechnicalFacets, metadata: dict[str, Any]) -> tuple[float, str]:
    """Return a bounded relevance multiplier and human-readable derived reason.

    Topic-less documents remain eligible.  They receive a modest penalty only
    for a high-confidence P0 technical intent, so authority cannot stand in
    for a known, incompatible diagnostic topic.
    """
    topic = str(metadata.get("topic") or "")
    normalized_topic = _TOPIC_ALIASES.get(topic, topic)
    predicted = facets.predicted_topic
    if predicted == "unknown":
        return 1.0, "no_high_confidence_technical_intent"
    if not normalized_topic:
        metadata_text = _fold(
            " ".join(
                str(metadata.get(key) or "") for key in ("title", "tags", "solution", "runbook")
            )
        )
        if (
            predicted == "vpn.forticlient_auth"
            and "vpn" in metadata_text
            and _has_any(metadata_text, ("authentication", "auth", "login", "dang nhap", "mfa", "profile", "certificate"))
        ):
            return 1.35, "inferred_vpn_auth_metadata_topic"
        return 0.72, "untyped_candidate_for_explicit_technical_intent"

    if predicted == "http.status_403":
        if normalized_topic == "http.status_403":
            return 1.35, "exact_http_status_intent"
        if normalized_topic in {"network.port_connectivity", "network.firewall_acl", "network.tcp_connectivity"}:
            return 0.15, "http_application_vs_raw_transport_incompatibility"
    if predicted == "network.port_connectivity":
        if normalized_topic == "network.port_connectivity":
            return 1.35, "exact_raw_transport_port_intent"
        if normalized_topic == "http.status_403":
            return 0.15, "raw_transport_port_vs_http_application_incompatibility"
    if predicted == "network.tcp_connectivity":
        if normalized_topic == "network.tcp_connectivity":
            return 1.35, "icmp_reachability_vs_tcp_connectivity"
        if normalized_topic in {"dns_proxy", "vpn.forticlient_auth"}:
            return 0.45, "tcp_connectivity_incompatible_topic"
    if predicted == "network.port_timeout":
        if normalized_topic == "network.tcp_failure_semantics":
            return 1.35, "timeout_failure_semantics"
        if normalized_topic == "network.service_not_listening":
            return 0.50, "timeout_vs_service_refusal_incompatibility"
        if normalized_topic == "network.firewall_acl":
            return 1.12, "timeout_path_or_filter_support"
    if predicted == "network.connection_refused":
        if normalized_topic == "network.service_not_listening":
            return 1.35, "refused_service_listener_intent"
        if normalized_topic == "network.tcp_failure_semantics":
            return 1.15, "refused_failure_semantics_support"
        if normalized_topic == "network.firewall_acl":
            return 0.50, "refused_vs_silent_filter_incompatibility"
    if predicted == "network.service_not_listening" and normalized_topic == "network.service_not_listening":
        return 1.35, "exact_service_listener_intent"
    if predicted == "vpn.forticlient_auth":
        if normalized_topic == "vpn.forticlient_auth":
            return 1.35, "vpn_authentication_intent"
        if normalized_topic in {"vpn.internal_resource_access", "routing"}:
            return 0.35, "vpn_auth_vs_post_connection_incompatibility"
    if predicted == "vpn.internal_resource_access":
        if normalized_topic == "vpn.internal_resource_access":
            return 1.35, "vpn_post_connection_internal_access"
        if normalized_topic == "routing":
            return 1.15, "vpn_post_connection_routing_support"
        if normalized_topic == "vpn.forticlient_auth":
            return 0.35, "vpn_post_connection_vs_auth_incompatibility"
    if predicted == "dns":
        if normalized_topic == "dns_proxy":
            return 1.35, "dns_diagnostic_intent"
        if normalized_topic == "routing":
            return 0.35, "dns_vs_routing_incompatibility"
    if predicted == "routing":
        if normalized_topic == "routing":
            return 1.35, "routing_or_split_tunnel_intent"
        if normalized_topic == "vpn.internal_resource_access":
            return 1.15, "routing_supporting_vpn_access"
        if normalized_topic == "dns_proxy":
            return 0.35, "routing_vs_dns_incompatibility"
    if predicted == "proxy" and normalized_topic == "dns_proxy":
        return 1.35, "proxy_diagnostic_intent"
    return 1.0, "topic_neutral"
