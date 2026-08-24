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
    has_http_marker = _has_any(text, ("http", "https", "api", "browser", "web", "website", "forbidden", "unauthorized", "gateway"))
    http_codes = [int(value) for value in re.findall(r"\b(401|403|404|500|502|504)\b", text)]
    port_match = _PORT_NUMBER.search(text)
    explicit_raw_port = (port_match is not None and not has_http_marker) or bool(
        re.search(r"\b(?:not|khong(?:\s+phai)?|no)\s+(?:a\s+)?http\b", text)
    )
    http_status = (
        403 if has_http_marker and "forbidden" in text and "401" not in text else (http_codes[-1] if has_http_marker and http_codes else None)
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

    # Specific technical intents (evaluated before generic transport fallbacks)
    if _has_any(text, ("ssh", "keygen", "ssh-keygen", "ed25519", "id_ed25519", "ssh-add", "publickey", "permission denied (publickey)", "known_hosts")):
        predicted = "developer.ssh"
    elif _has_any(text, ("git", "gcm", "git clone")) and _has_any(text, ("proxy", "sslverify", "cainfo", "certificate", "self-signed", "http.proxy")):
        predicted = "developer.git_proxy"
    elif _has_any(text, ("git", "github", "gitlab")) and _has_any(text, ("gcm", "credential manager", "submodule", "git lfs", "token", "clone", "push", "pull")):
        predicted = "developer.git_auth"
    elif _has_any(text, ("docker", "docker desktop", "lxssmanager", "container")):
        predicted = "developer.docker"
    elif _has_any(text, ("wsl", "wsl2", "wslconfig", "networkingmode mirrored")):
        predicted = "developer.wsl"
    elif _has_any(text, ("hyper-v", "default switch", "netnat", "virtual switch", "virtualization")):
        predicted = "developer.virtualization"
    elif _has_any(text, ("pip", "pypi", "pip.ini", "pip.conf", "trusted-host")):
        predicted = "developer.pip"
    elif _has_any(text, ("npm", "node.js", "strict-ssl", "cafile", "package.json")):
        predicted = "developer.npm"
    elif _has_any(text, ("powershell", "executionpolicy", "execution policy", "remotesigned")):
        predicted = "developer.powershell"
    elif _has_any(text, ("err_cert_authority_invalid", "err_ssl_protocol_error", "root ca", "certificate chain", "keychain", "ca-certificates", "x509")):
        predicted = "browser.ssl_certificate"
    elif _has_any(text, ("pac", "findproxyforurl", "wpad", "hsts", "net-internals")):
        predicted = "browser.proxy"
    elif _has_any(text, ("sql server", "ssms", "error 26", "error 10061", "1433", "pg_hba.conf", "scram-sha-256", "postgresql", "postgres", "dbeaver", "oracle", "tns-12541", "ora-12541", "lsnrctl", "tnsnames.ora", "libpq")):
        predicted = "database.client_connectivity"
    elif _has_any(text, ("rdp", "credssp", "mstsc", "0x204", "0x104", "remote desktop", "shadowing", "qwinsta")):
        predicted = "remote.rdp"
    elif _has_any(text, ("bitlocker", "tpm", "pcr", "recovery key", "manage-bde", "filevault")):
        predicted = "security.bitlocker"
    elif _has_any(text, ("defender", "smartscreen", "quarantine", "protection history", "mpcmdrun", "malware", "antivirus")):
        predicted = "security.defender"
    elif _has_any(text, ("mfa", "authenticator", "sspr", "windows hello", "0x80090016", "primary refresh token", "dsregcmd", "ngc", "mysignins")):
        predicted = "identity.mfa"
    elif _has_any(text, ("credential manager", "stale password", "domain trust")):
        predicted = "identity.mfa"
    elif _has_any(text, ("scanpst", "ost", "outlook profile", "mail 32 bit", "inbox repair tool")) or (_has_any(text, ("outlook",)) and _has_any(text, ("crash", "search", "index", "hỏng", "loi"))):
        predicted = "productivity.outlook"
    elif _has_any(text, ("teams",)) and _has_any(text, ("camera", "mic", "microphone", "screen recording", "privacy", "cache", "installed apps", "permissions")):
        predicted = "productivity.teams"
    elif _has_any(text, ("onedrive",)) and _has_any(text, ("file lock", "conflict", "processing changes", "reset", "treo")):
        predicted = "productivity.onedrive"
    elif _has_any(text, ("office", "m365")) and _has_any(text, ("unlicensed", "licensing", "activation", "token")):
        predicted = "productivity.office"
    elif _has_any(text, ("powercfg", "battery report", "chai pin")):
        predicted = "hardware.battery"
    elif _has_any(text, ("mdsched", "memory diagnostic", "ram 99%")):
        predicted = "hardware.ram"
    elif _has_any(text, ("spooler", "wsd", "port 9100", "print spooler", "hang doi may in")):
        predicted = "hardware.printer"
    elif _has_any(text, ("display hdr", "scaling", "mst", "4k bi mo", "scale dpi")):
        predicted = "hardware.display"
    elif _has_any(text, ("bluetooth le", "tai nghe bluetooth", "desync", "re mat tieng")):
        predicted = "hardware.audio"
    elif _has_any(text, ("dism", "sfc", "restorehealth", "scannow", "cleanup-image")):
        predicted = "os.windows_repair"
    elif _has_any(text, ("macos", "macbook", "apple", "finder", "smb://", "802.1x")):
        predicted = "client.macos_network"
    elif _has_any(text, ("ubuntu", "linux", "cifs", "mount.cifs", "nmcli", "cifs-utils")):
        predicted = "client.linux_network"
    elif http_status is not None:
        if http_status == 403:
            predicted = "http.status_403"
        elif http_status == 401:
            predicted = "http.status_401"
        elif http_status == 502:
            predicted = "http.status_502"
        elif http_status == 504:
            predicted = "http.status_504"
        else:
            predicted = "http.application"
    elif _has_any(text, ("502 bad gateway", "bad gateway", "502")) and has_http_marker:
        predicted = "http.status_502"
    elif _has_any(text, ("504 gateway timeout", "gateway timeout", "504")) and has_http_marker:
        predicted = "http.status_504"
    elif _has_any(text, ("401 unauthorized", "unauthorized vs forbidden", "401")) and has_http_marker:
        predicted = "http.status_401"
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

_INCOMPATIBLE_TOPICS: dict[str, set[str]] = {
    "developer.ssh": {"network.firewall_acl", "network.l3_vs_l4", "network.port_connectivity", "network.tcp_connectivity"},
    "developer.git_proxy": {"network.dns_proxy", "routing", "network.firewall_acl"},
    "developer.npm": {"browser.proxy", "network.dns_proxy"},
    "developer.pip": {"browser.ssl_certificate", "browser.proxy"},
    "database.client_connectivity": {"network.port_connectivity", "network.firewall_acl", "network.service_not_listening", "network.tcp_connectivity"},
    "productivity.outlook": {"hardware.battery", "hardware.ram", "hardware.display", "hardware.audio"},
    "productivity.teams": {"hardware.audio", "hardware.battery"},
    "productivity.onedrive": {"hardware.ram", "hardware.battery"},
    "identity.mfa": {"security.bitlocker"},
    "http.status_502": {"network.service_not_listening", "network.connection_refused"},
    "http.status_504": {"network.tcp.timeout_refused_reset", "network.port_timeout"},
    "http.status_401": {"http.status_403"},
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

    if predicted in _INCOMPATIBLE_TOPICS and normalized_topic in _INCOMPATIBLE_TOPICS[predicted]:
        return 0.20, f"{predicted}_vs_{normalized_topic}_incompatibility"

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

    # Expanded domain topic matching
    if predicted == normalized_topic:
        return 1.35, f"exact_{predicted}_intent"

    return 1.0, "topic_neutral"
