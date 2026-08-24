from src.services.source_provenance_service import knowledge_source_payload


def test_ticket_lesson_source_uses_the_original_ticket_reference():
    payload = knowledge_source_payload({
        "doc_id": "historical-00042",
        "metadata": {
            "title": "Resolved ticket lesson",
            "source_ticket_number": "INC-20260810-2047",
        },
    })

    assert payload == {
        "label": "Ticket #INC-20260810-2047",
        "kind": "ticket",
        "url": "/employee/tickets/reference/INC-20260810-2047",
    }


def test_standard_kb_source_uses_persisted_source_reader():
    payload = knowledge_source_payload({
        "doc_id": "kb-00042",
        "metadata": {"title": "VPN approved access guide"},
    })

    assert payload == {
        "label": "VPN approved access guide",
        "kind": "kb",
        "source_id": "kb-00042",
        "url": "/employee/kb?source_id=kb-00042",
    }


def test_verified_external_source_uses_exact_retrieved_url():
    payload = knowledge_source_payload({
        "doc_id": "web-01",
        "metadata": {
            "title": "Official printer documentation",
            "source_url": "https://support.example.test/printer",
        },
    })

    assert payload == {
        "label": "Official printer documentation",
        "kind": "web",
        "url": "https://support.example.test/printer",
    }
