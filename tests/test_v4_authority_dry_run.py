def test_v4_crawler_emits_authority_field() -> None:
    source = open("scripts/crawl_v4_pipeline.py", encoding="utf-8").read()
    assert "'authority': item.get('authority')" in source


def test_v4_builder_copies_existing_metadata_without_dropping_authority() -> None:
    source = open("scripts/build_v4_shadow.py", encoding="utf-8").read()
    assert "norm = dict(meta or {})" in source
    assert "'authority'" not in source[source.index("def normalize_meta"):source.index("settings = get_settings()")]


def test_v4_authority_patch_requires_explicit_apply_and_checks_invariants() -> None:
    source = open("scripts/patch_v4_authority_metadata.py", encoding="utf-8").read()
    assert 'parser.add_argument("--apply", action="store_true"' in source
    assert 'include=["documents", "metadatas", "embeddings"]' in source
    assert "collection.update(" in source
    assert "Invariant failed" in source
