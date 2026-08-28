from __future__ import annotations

from src.services.query_normalization_service import (
    extract_exact_technical_tokens,
)
from src.services.technical_intent_service import (
    infer_technical_facets,
    topic_compatibility,
)


def test_explicit_technical_query_identifies_intents() -> None:
    # SSH key
    facets_ssh = infer_technical_facets("ssh clone git permission denied publickey not firewall")
    assert facets_ssh.predicted_topic == "developer.ssh"

    # Git proxy
    facets_git_proxy = infer_technical_facets("cấu hình http.proxy trong git config clone repo")
    assert facets_git_proxy.predicted_topic == "developer.git_proxy"

    # Docker
    facets_docker = infer_technical_facets("docker desktop wsl2 backend crash restart lxssmanager")
    assert facets_docker.predicted_topic == "developer.docker"

    # MSSQL error 26
    facets_mssql = infer_technical_facets("sql server ssms error 26 locating server instance")
    assert facets_mssql.predicted_topic == "database.client_connectivity"

    # HTTP 504
    facets_504 = infer_technical_facets("http 504 gateway timeout upstream xử lý chậm")
    assert facets_504.predicted_topic == "http.status_504"

    # HTTP 403
    facets_403 = infer_technical_facets("lỗi http 403 forbidden trên api")
    assert facets_403.predicted_topic == "http.status_403"

    # Outlook ScanPST
    facets_scanpst = infer_technical_facets("outlook crash liên tục lúc mở sửa file ost bằng scanpst")
    assert facets_scanpst.predicted_topic == "productivity.outlook"


def test_cross_domain_topic_incompatibility_penalizes_hard_negatives() -> None:
    facets_ssh = infer_technical_facets("ssh clone git permission denied publickey not firewall")

    # Incompatible candidate: firewall ACL
    comp_neg, reason_neg = topic_compatibility(facets_ssh, {"topic": "network.firewall_acl"})
    assert comp_neg <= 0.35

    # Compatible candidate: developer.ssh
    comp_pos, reason_pos = topic_compatibility(facets_ssh, {"topic": "developer.ssh"})
    assert comp_pos >= 1.30


def test_generic_enterprise_query_remains_topic_neutral() -> None:
    facets = infer_technical_facets("hướng dẫn xin nghỉ phép và quy trình phê duyệt")
    assert facets.predicted_topic == "unknown"

    comp, reason = topic_compatibility(facets, {"topic": "internal_policy"})
    assert comp == 1.0
    assert reason == "no_high_confidence_technical_intent"


def test_exact_technical_token_extraction() -> None:
    tokens = extract_exact_technical_tokens("lỗi rdp 0x204 và credssp trên port 3389")
    assert "rdp" in tokens or "0x204" in tokens or "credssp" in tokens

    tokens_db = extract_exact_technical_tokens("sửa lỗi oracle sql developer ora-12541")
    assert "ora-12541" in tokens_db or "oracle" in tokens_db


def test_untyped_candidate_on_explicit_technical_query_is_bounded() -> None:
    facets = infer_technical_facets("sql server ssms error 26 locating server instance port 1433")
    comp, reason = topic_compatibility(facets, {})  # No metadata / untyped
    assert comp == 0.72
    assert "untyped_candidate" in reason


def test_evaluation_metadata_not_in_runtime_facets() -> None:
    facets = infer_technical_facets("test query")
    d = facets.public_dict()
    assert "query" not in d
    assert "expected_source_ids" not in d
    assert "primary_expected_source_ids" not in d
    assert "hard_negative_source_ids" not in d
