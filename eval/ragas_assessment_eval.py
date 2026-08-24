"""RAGAS-style end-to-end assessment for the help-desk RAG pipeline.

The script always produces deterministic local scores for:
- context_coverage: did retrieval bring enough relevant context?
- faithfulness: does the answer stay inside the retrieved/reference evidence?
- answer_focus: does the answer address the ticket without unsafe or irrelevant drift?

When ragas is installed and an evaluator LLM is configured, pass --use-ragas to
also run the official RAGAS metrics on the same golden dataset rows.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_settings
from src.prompts import (
    LLM_AS_JUDGE_SYSTEM_PROMPT,
    PRODUCTION_RAG_SYSTEM_PROMPT,
    build_judge_input,
)
from src.services.rag_service import get_collection_count, search_similar

# Keep exported names for scripts importing this module, while using the same
# versioned production/evaluator prompts as the application path.
RAGAS_ASSESSMENT_PROMPT = PRODUCTION_RAG_SYSTEM_PROMPT
EXTERNAL_JUDGE_PROMPT = LLM_AS_JUDGE_SYSTEM_PROMPT


def resolve_external_judge_config() -> tuple[str, str, str]:
    """Return an explicit judge config, or safely default to NVIDIA NIM.

    Explicit ``EVAL_JUDGE_*`` settings take precedence so deployments may use
    another approved OpenAI-compatible provider.  ``NVIDIA_API_KEY`` alone is
    enough for the project's synthetic evaluation workflow; it never changes
    the production answer-generation provider.
    """
    settings = get_settings()
    if settings.eval_judge_api_key and settings.eval_judge_model:
        return (
            settings.eval_judge_base_url.rstrip("/"),
            settings.eval_judge_api_key,
            settings.eval_judge_model,
        )
    if settings.nvidia_api_key:
        return (
            settings.nvidia_base_url.rstrip("/"),
            settings.nvidia_api_key,
            settings.nvidia_eval_judge_model,
        )
    raise RuntimeError(
        "Set EVAL_JUDGE_API_KEY + EVAL_JUDGE_MODEL, or set NVIDIA_API_KEY "
        "to use NVIDIA NIM for synthetic external evaluation."
    )


def get_external_judge_timeout_seconds() -> float:
    """Use a longer, evaluation-only timeout for hosted large judge models."""
    return get_settings().eval_judge_timeout_seconds


_STOPWORDS = {
    "a",
    "an",
    "and",
    "cai",
    "cho",
    "co",
    "cua",
    "duoc",
    "for",
    "hay",
    "in",
    "is",
    "khong",
    "la",
    "of",
    "on",
    "the",
    "to",
    "toi",
    "trong",
    "va",
    "voi",
}

_REFUSAL_MARKERS = (
    "khong the",
    "khong co thong tin",
    "khong tim thay",
    "khong du thong tin",
    "knowledge base",
    "tao ticket",
    "lien he it",
    "it security",
)


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_text(value: str) -> str:
    value = _strip_accents(value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def _contains(text: str, needle: str) -> bool:
    return normalize_text(needle) in normalize_text(text)


def _tokens(value: str) -> set[str]:
    normalized = normalize_text(value)
    return {
        token
        for token in re.findall(r"[a-z0-9]+", normalized)
        if len(token) > 2 and token not in _STOPWORDS
    }


def _ratio(hits: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return hits / total


def _score_expected_terms(text: str, terms: list[str]) -> tuple[float, list[str], list[str]]:
    hits = [term for term in terms if _contains(text, term)]
    misses = [term for term in terms if term not in hits]
    return _ratio(len(hits), len(terms)), hits, misses


def _retrieved_text(retrieved: list[dict]) -> str:
    parts = []
    for item in retrieved:
        metadata = item.get("metadata", {})
        parts.append(f"{metadata.get('title', '')}\n{metadata.get('tags', '')}\n{item.get('content', '')}")
    return "\n\n".join(parts)


def _retrieved_titles(retrieved: list[dict]) -> list[str]:
    return [item.get("metadata", {}).get("title", "") for item in retrieved]


def context_coverage(case: dict, retrieved: list[dict]) -> dict:
    titles = _retrieved_titles(retrieved)
    retrieved_blob = _retrieved_text(retrieved)
    expected_titles = case.get("expected_titles", [])
    expected_terms = case.get("expected_context_terms", [])

    title_hits = [
        expected
        for expected in expected_titles
        if any(_contains(title, expected) or _contains(expected, title) for title in titles)
    ]
    term_score, term_hits, term_misses = _score_expected_terms(retrieved_blob, expected_terms)

    if not expected_titles and not expected_terms:
        score = 1.0 if not retrieved else 0.5
    elif expected_titles and expected_terms:
        score = 0.55 * _ratio(len(title_hits), len(expected_titles)) + 0.45 * term_score
    elif expected_titles:
        score = _ratio(len(title_hits), len(expected_titles))
    else:
        score = term_score

    return {
        "score": round(score, 4),
        "title_hits": title_hits,
        "term_hits": term_hits,
        "term_misses": term_misses,
        "retrieved_titles": titles,
    }


def faithfulness(case: dict, answer: str, retrieved: list[dict]) -> dict:
    if not answer:
        return {"score": None, "unsupported_terms": [], "forbidden_hits": []}

    retrieved_blob = _retrieved_text(retrieved)
    reference = case.get("reference_answer", "")
    evidence_blob = f"{retrieved_blob}\n{reference}"
    expected_terms = case.get("expected_answer_terms", [])
    forbidden_terms = case.get("forbidden_answer_terms", [])
    expected_behavior = case.get("expected_behavior", "")

    answer_expected_hits = [term for term in expected_terms if _contains(answer, term)]
    supported_hits = [term for term in answer_expected_hits if _contains(evidence_blob, term)]
    unsupported_terms = [term for term in answer_expected_hits if term not in supported_hits]
    forbidden_hits = [term for term in forbidden_terms if _contains(answer, term)]

    if expected_behavior in {"insufficient_context", "refuse_unsafe"}:
        has_refusal = any(marker in normalize_text(answer) for marker in _REFUSAL_MARKERS)
        score = 1.0 if has_refusal and not forbidden_hits else 0.25 if forbidden_hits else 0.65
    else:
        support_score = _ratio(len(supported_hits), len(answer_expected_hits) or len(expected_terms))
        score = max(0.0, support_score - 0.25 * len(forbidden_hits))

    return {
        "score": round(score, 4),
        "supported_terms": supported_hits,
        "unsupported_terms": unsupported_terms,
        "forbidden_hits": forbidden_hits,
    }


def answer_focus(case: dict, answer: str) -> dict:
    if not answer:
        return {"score": None, "term_hits": [], "term_misses": [], "forbidden_hits": []}

    expected_terms = case.get("expected_answer_terms", [])
    forbidden_terms = case.get("forbidden_answer_terms", [])
    term_score, term_hits, term_misses = _score_expected_terms(answer, expected_terms)
    forbidden_hits = [term for term in forbidden_terms if _contains(answer, term)]

    query_tokens = _tokens(case.get("query", ""))
    answer_tokens = _tokens(answer)
    query_overlap = _ratio(len(query_tokens & answer_tokens), min(len(query_tokens), 8))
    score = 0.75 * term_score + 0.25 * query_overlap
    if forbidden_hits:
        score = max(0.0, score - 0.3 * len(forbidden_hits))

    return {
        "score": round(score, 4),
        "term_hits": term_hits,
        "term_misses": term_misses,
        "forbidden_hits": forbidden_hits,
    }


def build_context_prompt(case: dict, retrieved: list[dict]) -> str:
    # `build_judge_input` has the exact same data boundary but includes an
    # actual answer.  For generation we keep only the two production fields.
    from src.prompts import build_authorized_evidence

    return f"""[AUTHORIZED_EVIDENCE]
{build_authorized_evidence(retrieved)}

[USER QUESTION]
{case["query"]}"""


async def generate_answer(case: dict, retrieved: list[dict]) -> str:
    from src.services.llm import get_rag_llm

    llm = get_rag_llm()
    response = await llm.ainvoke(
        [
            SystemMessage(content=RAGAS_ASSESSMENT_PROMPT),
            HumanMessage(content=build_context_prompt(case, retrieved)),
        ]
    )
    return response.content.strip()


def build_ragas_row(case: dict, answer: str, retrieved: list[dict]) -> dict:
    return {
        "question": case["query"],
        "answer": answer,
        "contexts": [item.get("content", "") for item in retrieved],
        "ground_truth": case.get("reference_answer", ""),
    }


def validate_external_judge_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize untrusted LLM output to the published quality-gate schema."""
    def score(field: str) -> float:
        try:
            value = float(payload.get(field, 0.0))
        except (TypeError, ValueError):
            return 0.0
        return round(value, 4) if 0.0 <= value <= 1.0 else 0.0

    faithfulness_score = score("faithfulness_score")
    relevance_score = score("relevance_score")
    completeness_score = score("completeness_score")
    abstention_score = score("abstention_score")
    # Always calculate the aggregate locally rather than trusting the judge.
    overall_score = round(
        faithfulness_score * 0.45
        + relevance_score * 0.15
        + completeness_score * 0.30
        + abstention_score * 0.10,
        2,
    )
    allowed_failures = {
        "hallucination", "incomplete", "irrelevant", "off_topic", "incorrect_refusal",
        "action_grounding_failure", "citation_error", "instruction_following_failure",
    }
    failure_types = [
        item for item in payload.get("failure_types", [])
        if isinstance(item, str) and item in allowed_failures
    ]
    reported_hallucination = payload.get("has_hallucination", False)
    has_hallucination = (
        reported_hallucination if isinstance(reported_hallucination, bool) else False
    ) or "hallucination" in failure_types
    hard_failure = has_hallucination or any(
        item in failure_types
        for item in ("action_grounding_failure", "citation_error", "instruction_following_failure")
    )
    passed = (
        faithfulness_score >= 0.80
        and relevance_score >= 0.70
        and completeness_score >= 0.70
        and abstention_score >= 0.70
        and overall_score >= 0.75
        and not hard_failure
    )
    return {
        "faithfulness_score": faithfulness_score,
        "relevance_score": relevance_score,
        "completeness_score": completeness_score,
        "abstention_score": abstention_score,
        "overall_score": overall_score,
        "passed": passed,
        "has_hallucination": has_hallucination,
        "failure_types": failure_types,
        "unsupported_claims": [str(item)[:300] for item in payload.get("unsupported_claims", []) if isinstance(item, str)],
        "missing_points": [str(item)[:300] for item in payload.get("missing_points", []) if isinstance(item, str)],
        "reasoning": str(payload.get("reasoning", ""))[:500],
    }


def failed_external_judge_result(reason: str) -> dict[str, Any]:
    """Fail the gate closed when the evaluation provider is unavailable or malformed."""
    return {
        "faithfulness_score": 0.0,
        "relevance_score": 0.0,
        "completeness_score": 0.0,
        "abstention_score": 0.0,
        "overall_score": 0.0,
        "passed": False,
        "has_hallucination": False,
        "failure_types": [],
        "unsupported_claims": [],
        "missing_points": [],
        "reasoning": f"External judge unavailable or returned invalid JSON: {reason}"[:500],
    }


async def judge_with_external_llm(
    case: dict,
    answer: str,
    retrieved: list[dict],
    *,
    include_raw_evidence: bool = False,
) -> dict[str, Any]:
    """Call a separately configured judge without exporting KB content by default."""
    base_url, api_key, model = resolve_external_judge_config()
    # Source titles make the judgment auditable while keeping real KB content in
    # process.  Raw text needs a separate, deliberate acknowledgement because a
    # golden question can still retrieve a confidential document by accident.
    # External judging is limited to explicitly approved synthetic fixtures.
    # Without raw evidence, the judge can assess relevance but cannot reliably
    # validate grounding, so the gate should be run with the opt-in flag.
    evidence = retrieved[:5] if include_raw_evidence else [
        {"metadata": {"title": item.get("metadata", {}).get("title", "")}}
        for item in retrieved[:5]
    ]
    judge_input = build_judge_input(
        question=case["query"],
        retrieved_context=evidence,
        actual_answer=answer,
    )
    url = base_url + "/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=get_external_judge_timeout_seconds()) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "temperature": 0, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": EXTERNAL_JUDGE_PROMPT}, {"role": "user", "content": judge_input}]},
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        payload = json.loads(content)
        if not isinstance(payload, dict):
            return failed_external_judge_result("response was not a JSON object")
        return validate_external_judge_result(payload)
    except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return failed_external_judge_result(type(exc).__name__)


def load_answers(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return {str(key): str(value) for key, value in payload.items()}
    return {str(item["id"]): str(item["answer"]) for item in payload}


async def evaluate_cases(
    cases: list[dict],
    *,
    top_k: int,
    answers: dict[str, str] | None = None,
    generate_answers: bool = False,
    judge_external: bool = False,
    external_judge_include_raw_evidence: bool = False,
) -> dict:
    answers = answers or {}
    settings = get_settings()
    results = []

    for case in cases:
        retrieved = search_similar(
            query=case["query"],
            n_results=top_k,
            category_filter=case.get("category"),
            user_company_unit=case.get("company_unit"),
            user_department=case.get("department"),
        )
        answer = answers.get(case["id"], "")
        if generate_answers and not answer:
            answer = await generate_answer(case, retrieved)

        coverage = context_coverage(case, retrieved)
        faithful = faithfulness(case, answer, retrieved)
        focus = answer_focus(case, answer)
        external_judge = (
            await judge_with_external_llm(
                case,
                answer,
                retrieved,
                include_raw_evidence=external_judge_include_raw_evidence,
            )
            if judge_external and answer
            else None
        )
        result = {
            "id": case["id"],
            "type": case.get("type", ""),
            "query": case["query"],
            "expected_behavior": case.get("expected_behavior", ""),
            "answer": answer,
            "context_coverage": coverage,
            "faithfulness": faithful,
            "answer_focus": focus,
            "external_judge": external_judge,
            "ragas_row": build_ragas_row(case, answer, retrieved),
        }
        results.append(result)

    def average(metric_name: str) -> float | None:
        values = [
            item[metric_name]["score"]
            for item in results
            if item[metric_name]["score"] is not None
        ]
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    judge_rows = [item["external_judge"] for item in results if item["external_judge"]]
    judge_averages = {
        metric: round(sum(row[metric] for row in judge_rows) / len(judge_rows), 4) if judge_rows else None
        for metric in ("faithfulness_score", "relevance_score", "completeness_score", "abstention_score", "overall_score")
    }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "collection": settings.chroma_collection_name,
        "embedding_model": settings.embedding_model,
        "collection_count": get_collection_count(),
        "case_count": len(cases),
        "top_k": top_k,
        "averages": {
            "context_coverage": average("context_coverage"),
            "faithfulness": average("faithfulness"),
            "answer_focus": average("answer_focus"),
        },
        "external_judge_averages": judge_averages,
        "results": results,
    }


def run_official_ragas(report: dict) -> dict[str, Any]:
    try:
        from datasets import Dataset
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
    except ImportError as exc:
        raise RuntimeError(
            "Install ragas and datasets, then configure an evaluator LLM before using --use-ragas."
        ) from exc

    rows = [
        item["ragas_row"]
        for item in report["results"]
        if item["ragas_row"]["answer"] and item["ragas_row"]["contexts"]
    ]
    if not rows:
        return {"skipped": "No generated/provided answers and contexts were available."}

    dataset = Dataset.from_list(rows)
    result = ragas_evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    if hasattr(result, "to_pandas"):
        return {"rows": result.to_pandas().to_dict(orient="records")}
    return {"result": str(result)}


def markdown_report(report: dict) -> str:
    averages = report["averages"]
    lines = [
        "# RAGAS Assessment Evaluation",
        "",
        f"- Collection: `{report['collection']}`",
        f"- Embedding model: `{report['embedding_model']}`",
        f"- Documents: {report['collection_count']}",
        f"- Cases: {report['case_count']}",
        f"- Top K: {report['top_k']}",
        f"- Context coverage: {averages['context_coverage']}",
        f"- Faithfulness: {averages['faithfulness']}",
        f"- Answer focus: {averages['answer_focus']}",
        f"- External judge (normalized /1): {report['external_judge_averages']}",
        "",
        "| Case | Type | Context | Faithful | Focus | Retrieved |",
        "|---|---|---:|---:|---:|---|",
    ]
    for item in report["results"]:
        titles = ", ".join(item["context_coverage"]["retrieved_titles"][:3])
        safe_titles = titles.replace("|", "\\|")
        faith_score = item["faithfulness"]["score"]
        focus_score = item["answer_focus"]["score"]
        lines.append(
            f"| {item['id']} | {item['type']} | "
            f"{item['context_coverage']['score']} | {faith_score} | {focus_score} | "
            f"{safe_titles} |"
        )
    return "\n".join(lines) + "\n"


def write_ragas_dataset(report: dict, path: Path) -> None:
    rows = [item["ragas_row"] for item in report["results"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAG with a RAGAS-style golden set")
    parser.add_argument("--cases", type=Path, default=Path("eval/ragas_golden_dataset.json"))
    parser.add_argument("--answers-json", type=Path)
    parser.add_argument("--generate-answers", action="store_true")
    parser.add_argument("--judge-external", action="store_true", help="Use the separately configured external LLM judge.")
    parser.add_argument("--allow-external-judge", action="store_true", help="Required acknowledgement: only synthetic, non-confidential evaluation data may leave this machine.")
    parser.add_argument("--allow-external-evidence", action="store_true", help="Explicitly allow raw retrieved KB text to be sent to the external judge. Do not use with production KB.")
    parser.add_argument("--use-ragas", action="store_true")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--minimum-context-coverage", type=float, default=0.75)
    parser.add_argument("--minimum-faithfulness", type=float, default=0.75)
    parser.add_argument("--minimum-answer-focus", type=float, default=0.70)
    parser.add_argument(
        "--output-json", type=Path, default=Path("eval/results/ragas_assessment_report.json")
    )
    parser.add_argument(
        "--output-md", type=Path, default=Path("eval/results/ragas_assessment_report.md")
    )
    parser.add_argument(
        "--ragas-dataset-json", type=Path, default=Path("eval/results/ragas_dataset.json")
    )
    args = parser.parse_args()

    if args.judge_external and not args.allow_external_judge:
        parser.error("--judge-external requires --allow-external-judge to prevent accidental external data egress.")
    if args.allow_external_evidence and not args.judge_external:
        parser.error("--allow-external-evidence can only be used together with --judge-external.")

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    answers = load_answers(args.answers_json)
    report = asyncio.run(
        evaluate_cases(
            cases,
            top_k=args.top_k,
            answers=answers,
            generate_answers=args.generate_answers,
            judge_external=args.judge_external,
            external_judge_include_raw_evidence=args.allow_external_evidence,
        )
    )

    if args.use_ragas:
        report["official_ragas"] = run_official_ragas(report)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.write_text(markdown_report(report), encoding="utf-8")
    write_ragas_dataset(report, args.ragas_dataset_json)

    averages = report["averages"]
    print(
        "Context={context} Faithfulness={faith} Focus={focus}".format(
            context=averages["context_coverage"],
            faith=averages["faithfulness"],
            focus=averages["answer_focus"],
        )
    )

    checks = [
        averages["context_coverage"] is not None
        and averages["context_coverage"] >= args.minimum_context_coverage,
    ]
    if args.generate_answers or args.answers_json:
        checks.extend(
            [
                averages["faithfulness"] is not None
                and averages["faithfulness"] >= args.minimum_faithfulness,
                averages["answer_focus"] is not None
                and averages["answer_focus"] >= args.minimum_answer_focus,
            ]
        )
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
