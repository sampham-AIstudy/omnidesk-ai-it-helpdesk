from eval.evidence_ordering_regression_autopsy_v1_2 import IMPROVED_IDS, REGRESSED_IDS, run


def test_autopsy_uses_existing_ab_movements_and_rejects_ordering() -> None:
    result = run()

    assert result["decision"] == "ABANDON_EVIDENCE_ORDERING_CHANGE"
    assert result["improved_case_ids"] == list(IMPROVED_IDS)
    assert result["regressed_case_ids"] == list(REGRESSED_IDS)
    assert result["trusted_property_analysis"]["separates_groups"] is False
    assert result["metadata"]["generation_calls"] == 0
    assert len(result["cases"]) == 8


def test_autopsy_claim_matrix_keeps_evaluation_metadata_out_of_runtime() -> None:
    result = run()
    rows = {row["case_id"]: row for row in result["cases"]}

    assert rows["GT-020"]["primary_cause"] == "QUERY_ANCHOR_HELPED"
    assert rows["GT-026"]["primary_cause"] == "CONDITIONAL_EVIDENCE_MISREAD"
    assert any(not claim["supported"] for claim in rows["GT-076"]["claim_coverage"])
