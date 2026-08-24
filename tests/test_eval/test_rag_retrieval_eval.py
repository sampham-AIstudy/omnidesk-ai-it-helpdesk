from eval.rag_retrieval_eval import evaluate


def test_evaluate_computes_hit_rates(monkeypatch):
    responses = {
        "first": ["Expected document", "Other"],
        "second": ["Other", "Expected document"],
        "miss": ["Other"],
    }

    def fake_search_similar(query, category_filter, n_results):
        return [{"doc_id": f"{query}-{index}", "metadata": {"title": title}} for index, title in enumerate(responses[query])]

    monkeypatch.setattr("eval.rag_retrieval_eval.search_similar", fake_search_similar)
    monkeypatch.setattr("eval.rag_retrieval_eval.get_collection_count", lambda: 10)
    cases = [
        {"query": "first", "expected_title": "Expected", "category": "network"},
        {"query": "second", "expected_title": "Expected", "category": "network"},
        {"query": "miss", "expected_title": "Expected", "category": "network"},
    ]

    report = evaluate(cases, top_k=3)

    assert report["hit_at_1"] == 1 / 3
    assert report["hit_at_3"] == 2 / 3
    assert report["recall_at_3"] == 2 / 3
    assert report["mrr"] == 0.5
    assert report["source_relevance"] == 2 / 5
    assert report["noise_rate"] == 3 / 5
    assert report["duplicate_source_rate"] == 0.0


def test_evaluate_reports_duplicate_and_noise_sources(monkeypatch):
    def fake_search_similar(query, category_filter, n_results):
        return [
            {"doc_id": "vpn-1", "metadata": {"title": "VPN guide"}, "relevance_score": 0.92},
            {"doc_id": "vpn-1", "metadata": {"title": "VPN guide"}, "relevance_score": 0.91},
            {"doc_id": "mail-1", "metadata": {"title": "Mailbox guide"}, "relevance_score": 0.88},
        ]

    monkeypatch.setattr("eval.rag_retrieval_eval.search_similar", fake_search_similar)
    monkeypatch.setattr("eval.rag_retrieval_eval.get_collection_count", lambda: 3)

    report = evaluate([{"query": "vpn", "category": "network", "expected_title": "VPN"}], top_k=3)

    assert report["source_relevance"] == 2 / 3
    assert report["noise_rate"] == 1 / 3
    assert report["duplicate_source_rate"] == 1 / 3
