from src.services.rag_service import _metadata_allowed


def test_rag_metadata_allows_global_docs():
    metadata = {"applicable_to_all": True, "company_unit": "all"}

    assert _metadata_allowed(metadata, "healthcare", "ICU") is True


def test_rag_metadata_blocks_other_company_docs():
    metadata = {"applicable_to_all": False, "company_unit": "automotive"}

    assert _metadata_allowed(metadata, "healthcare", "ICU") is False


def test_rag_metadata_blocks_other_department_docs():
    metadata = {
        "applicable_to_all": False,
        "company_unit": "healthcare",
        "department": "Finance",
    }

    assert _metadata_allowed(metadata, "healthcare", "ICU") is False


def test_rag_metadata_allows_matching_department_docs():
    metadata = {
        "applicable_to_all": False,
        "company_unit": "healthcare",
        "department": "ICU",
    }

    assert _metadata_allowed(metadata, "healthcare", "ICU") is True
