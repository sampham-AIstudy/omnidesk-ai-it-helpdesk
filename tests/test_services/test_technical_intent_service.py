"""Semantic-variant coverage for deterministic technical intent facets."""
from __future__ import annotations

import pytest

from src.services.technical_intent_service import infer_technical_facets, topic_compatibility


@pytest.mark.parametrize(
    ("query", "topic", "protocol", "layer"),
    [
        ("ping ok ma 443 timeout", "network.tcp_connectivity", "tcp", "l4"),
        ("icmp duoc ma tcp ko duoc", "network.tcp_connectivity", "tcp", "l4"),
        ("cổng 403 bị timeout", "network.port_connectivity", "tcp", "l4"),
        ("api trả mã 403", "http.status_403", "http", "application"),
        ("403 forbidden từ web", "http.status_403", "http", "application"),
        ("server từ chối kết nối", "network.connection_refused", "unknown", "unknown"),
        ("connection refused", "network.connection_refused", "unknown", "unknown"),
        ("vpn login không được", "vpn.forticlient_auth", "unknown", "unknown"),
        ("vpn vào rồi nhưng không thấy server", "vpn.internal_resource_access", "unknown", "unknown"),
        ("dns resolve được nhưng route fail", "dns", "unknown", "unknown"),
        ("định tuyến VPN không tới server nội bộ", "routing", "unknown", "unknown"),
    ],
)
def test_semantic_variants_infer_generalized_technical_intent(
    query: str, topic: str, protocol: str, layer: str
) -> None:
    facets = infer_technical_facets(query)
    assert facets.predicted_topic == topic
    assert facets.protocol == protocol
    assert facets.network_layer == layer


def test_raw_tcp_port_is_strongly_incompatible_with_http_status_article() -> None:
    facets = infer_technical_facets("tcp 403 timeout")
    port_match, _ = topic_compatibility(facets, {"topic": "network.port_connectivity"})
    http_mismatch, _ = topic_compatibility(facets, {"topic": "http.status_403"})
    assert port_match > 1.0
    assert http_mismatch < 0.5


def test_http_403_is_strongly_incompatible_with_raw_port_article() -> None:
    facets = infer_technical_facets("HTTP 403 Forbidden khi gọi API")
    http_match, _ = topic_compatibility(facets, {"topic": "http.status_403"})
    port_mismatch, _ = topic_compatibility(facets, {"topic": "network.port_connectivity"})
    assert http_match > 1.0
    assert port_mismatch < 0.5


def test_same_topic_keeps_authority_available_for_final_ordering() -> None:
    facets = infer_technical_facets("FortiClient login failed")
    internal, _ = topic_compatibility(facets, {"topic": "vpn.forticlient.ssl_vpn", "source": "internal_curated_kb"})
    vendor, _ = topic_compatibility(facets, {"topic": "vpn.forticlient.ssl_vpn", "source": "official_web_documentation"})
    assert internal == vendor == 1.35
