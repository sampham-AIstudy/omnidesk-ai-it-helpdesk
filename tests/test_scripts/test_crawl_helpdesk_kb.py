from scripts.crawl_helpdesk_kb import (
    ArticleTextParser,
    chunk_blocks,
    deduplicate_blocks,
)


def test_article_parser_removes_navigation_and_scripts():
    parser = ArticleTextParser()
    parser.feed(
        """
        <html><head><title>Printer help</title><script>ignore me forever</script></head>
        <body><nav><p>Navigation should disappear</p></nav>
        <main><h1>Printer is offline</h1>
        <p>Check the printer power and network connection before continuing.</p></main>
        </body></html>
        """
    )

    assert parser.page_title == "Printer help"
    assert parser.blocks == [
        "Printer is offline",
        "Check the printer power and network connection before continuing.",
    ]


def test_deduplicate_blocks_is_case_and_punctuation_insensitive():
    blocks = ["Run the troubleshooter first.", "RUN the troubleshooter first!", "Next step"]

    assert deduplicate_blocks(blocks) == ["Run the troubleshooter first.", "Next step"]


def test_chunk_blocks_respects_limit_and_keeps_overlap():
    blocks = ["A" * 90, "B" * 90, "C" * 90]

    chunks = chunk_blocks(blocks, max_chars=200, overlap_blocks=1)

    assert len(chunks) == 2
    assert chunks[0].endswith("B" * 90)
    assert chunks[1].startswith("B" * 90)
    assert all(len(chunk) <= 200 for chunk in chunks)
