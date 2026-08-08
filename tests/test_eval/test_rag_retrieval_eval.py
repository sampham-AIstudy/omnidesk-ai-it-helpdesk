from eval.rag_retrieval_eval import evaluate


def test_evaluate_computes_hit_rates(monkeypatch):
    responses = {
        "first": ["Expected document", "Other"],
        "second": ["Other", "Expected document"],
        "miss": ["Other"],
    }

    def fake_search_similar(query, category_filter, n_results):
        return [{"metadata": {"title": title}} for title in responses[query]]

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
    assert report["mrr"] == 0.5
