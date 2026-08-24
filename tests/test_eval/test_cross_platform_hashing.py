from __future__ import annotations

import hashlib
from pathlib import Path

from eval.contract_kb_fixture import contract_metadata
from eval.evaluation_contract import (
    canonicalize_text_bytes,
    load_lock,
    sha256_file,
    sha256_file_bytes,
    sha256_text_file,
    validate_lock,
)
from scripts.run_retrieval_gate import compute_file_sha256

ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_GOLDEN_PATH = ROOT / "eval" / "retrieval_golden_v1.json"
CANONICAL_RETRIEVAL_GOLDEN_SHA256 = "ca55989f841372f75f299492f4be8a3f9215acc37b7a7da72ecc7498b1eb59b3"


def test_canonicalize_text_bytes_normalizes_line_endings() -> None:
    assert canonicalize_text_bytes(b"a\r\nb\r\n") == b"a\nb\n"
    assert canonicalize_text_bytes(b"a\nb\n") == b"a\nb\n"
    assert canonicalize_text_bytes(b"a\rb\r") == b"a\nb\n"
    assert canonicalize_text_bytes(b"a\r\nb\nc\rd\r\n") == b"a\nb\nc\nd\n"


def test_lf_and_crlf_produce_identical_canonical_sha(tmp_path: Path) -> None:
    lf_file = tmp_path / "lf.txt"
    crlf_file = tmp_path / "crlf.txt"
    cr_file = tmp_path / "cr.txt"

    lf_file.write_bytes(b"alpha\nbeta\ngamma\n")
    crlf_file.write_bytes(b"alpha\r\nbeta\r\ngamma\r\n")
    cr_file.write_bytes(b"alpha\rbeta\rgamma\r")

    assert sha256_text_file(lf_file) == sha256_text_file(crlf_file)
    assert sha256_text_file(lf_file) == sha256_text_file(cr_file)
    assert sha256_file(lf_file) == sha256_file(crlf_file)


def test_canonical_sha_detects_content_changes(tmp_path: Path) -> None:
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"

    file_a.write_bytes(b"a\nb\n")
    file_b.write_bytes(b"a\nc\n")

    assert sha256_text_file(file_a) != sha256_text_file(file_b)


def test_raw_byte_sha_distinguishes_line_endings(tmp_path: Path) -> None:
    lf_file = tmp_path / "lf.txt"
    crlf_file = tmp_path / "crlf.txt"

    lf_file.write_bytes(b"a\nb\n")
    crlf_file.write_bytes(b"a\r\nb\r\n")

    assert sha256_file_bytes(lf_file) != sha256_file_bytes(crlf_file)
    assert sha256_file_bytes(lf_file) == hashlib.sha256(b"a\nb\n").hexdigest()
    assert sha256_file_bytes(crlf_file) == hashlib.sha256(b"a\r\nb\r\n").hexdigest()


def test_retrieval_golden_canonical_sha_preserved() -> None:
    assert RETRIEVAL_GOLDEN_PATH.exists()
    digest = compute_file_sha256(RETRIEVAL_GOLDEN_PATH)
    assert digest == CANONICAL_RETRIEVAL_GOLDEN_SHA256


def test_validate_lock_succeeds_on_v1_2_lock() -> None:
    lock = load_lock(ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2.json")
    errors = validate_lock(ROOT, lock)
    assert errors == []


def test_validate_lock_succeeds_on_v1_2_full_lock() -> None:
    lock = load_lock(ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json")
    errors = validate_lock(ROOT, lock)
    assert errors == []


def test_contract_kb_fixture_metadata_uses_canonical_hash() -> None:
    metadata = contract_metadata()
    assert metadata["source_sha256"] == "e8e0184ce939e45f7dc40b1e6d77bdbdea762e338e5e207dcb66a0a78796f6e8"
