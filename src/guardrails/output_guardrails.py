"""
Output Guardrails Module
Handles sensitive data detection (Microsoft Presidio PII anonymizer + secret regex redaction),
OpenAI Moderation API, Gemini Safety Judge, and Groundedness evaluation.
"""

import logging
import re
from typing import Any, Dict, List, Optional

import requests

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Microsoft Presidio if installed
_presidio_analyzer = None
_presidio_anonymizer = None

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

    _presidio_analyzer = AnalyzerEngine()
    _presidio_anonymizer = AnonymizerEngine()
    logger.info("Microsoft Presidio Analyzer & Anonymizer initialized successfully")
except Exception as e:
    logger.warning(f"Microsoft Presidio not initialized: {e}. Falling back to custom regex redaction.")

SECRET_PATTERNS = [
    # Database connection string
    (r"(mysql|postgresql|sqlite\+aiosqlite|mongodb|redis|oracle)://[^\s'\"]+", "[REDACTED_DATABASE_URI]"),
    # API key / Token patterns
    (r"(?i)(api[_-]?key|secret|token|bearer|password|passwd|pwd|auth)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?", r"\1=[REDACTED_SECRET]"),
    (r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED_OPENAI_KEY]"),
    (r"AIzaSy[A-Za-z0-9_-]{33}", "[REDACTED_GOOGLE_KEY]"),
    (r"bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", "[REDACTED_BEARER_TOKEN]"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "[REDACTED_JWT_TOKEN]"),
    # Private Key
    (r"-----BEGIN (RSA|EC|PGP|OPENSSH) PRIVATE KEY-----[\s\S]+?-----END \1 PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
    # PII Fallback Regex (Vietnamese Phone, CCCD/CMND, IP)
    (r"\b(03|05|07|08|09)\d{8}\b", "[REDACTED_PHONE_NUMBER]"),
    (r"\b\d{9}\b|\b\d{12}\b", "[REDACTED_ID_NUMBER]"),
    (r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "[REDACTED_IP_ADDRESS]"),
]


def redact_secrets_and_pii(text: str) -> Dict[str, Any]:
    """Redact sensitive PII and secrets using Presidio + Regex."""
    if not text:
        return {"safe": True, "redacted": "", "issues": [], "severity": "LOW"}

    issues = []
    redacted_text = text

    # Presidio PII Scanning (Targeted sensitive entities to prevent English NER false positives on Vietnamese text)
    if _presidio_analyzer and _presidio_anonymizer:
        try:
            target_entities = [
                "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "CRYPTO",
                "IP_ADDRESS", "US_SSN", "PASSPORT", "IBAN_CODE"
            ]
            results = _presidio_analyzer.analyze(text=text, entities=target_entities, language="en")
            if results:
                anonymized_result = _presidio_anonymizer.anonymize(text=text, analyzer_results=results)
                redacted_text = anonymized_result.text
                for r in results:
                    issues.append(f"Presidio detected {r.entity_type}")
        except Exception as e:
            logger.warning(f"Presidio analysis error: {e}")

    # Regex Secret & Credential Scanning
    for pattern, replacement in SECRET_PATTERNS:
        if re.search(pattern, redacted_text):
            issues.append(f"Matched secret pattern: {pattern}")
            redacted_text = re.sub(pattern, replacement, redacted_text)

    severity = "LOW"
    if len(issues) > 0:
        severity = "HIGH" if any("DATABASE" in i or "KEY" in i or "TOKEN" in i for i in issues) else "MEDIUM"

    return {
        "safe": len(issues) == 0,
        "issues": issues,
        "redacted": redacted_text,
        "severity": severity,
    }


def check_openai_moderation(text: str) -> Dict[str, Any]:
    """Check text using OpenAI Moderation API if key is available."""
    api_key = settings.openai_moderation_api
    if not api_key:
        return {"flagged": False, "reason": "No OpenAI Moderation API key configured"}

    url = "https://api.openai.com/v1/moderations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"input": text}

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            results = data.get("results", [{}])[0]
            flagged = results.get("flagged", False)
            categories = [cat for cat, val in results.get("categories", {}).items() if val]
            return {"flagged": flagged, "categories": categories, "raw": results}
    except Exception as e:
        logger.warning(f"OpenAI Moderation API error: {e}")
    return {"flagged": False}


def gemini_safety_judge(prompt: str, response: str) -> Dict[str, Any]:
    """Evaluate output safety using Google Gemini API as Safety Judge."""
    api_key = settings.google_api_key
    if not api_key:
        return {"safe": True, "verdict": "SAFE", "reason": "Gemini API key not set, fallback SAFE"}

    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)
        
        judge_prompt = f"""You are a Security Judge evaluating AI agent outputs for safety and compliance.
User Request: {prompt}
Agent Response: {response}

Analyze if the agent response contains:
1. Leaked secrets, credentials, or private internal infrastructure information
2. Unsafe or harmful instructions
3. Prompt injection vulnerabilities

Respond in JSON format:
{{"safe": true/false, "verdict": "SAFE" / "UNSAFE", "reason": "explanation"}}
"""
        result = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=judge_prompt,
        )
        text_out = result.text.strip()
        safe = "true" in text_out.lower() and "unsafe" not in text_out.lower()
        return {"safe": safe, "verdict": "SAFE" if safe else "UNSAFE", "raw": text_out}
    except Exception as e:
        logger.warning(f"Gemini Safety Judge error: {e}")
        return {"safe": True, "verdict": "SAFE", "reason": f"Fallback due to Gemini error: {e}"}


def evaluate_groundedness(answer: str, context_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verify if the generated troubleshooting instructions are grounded in retrieved KB docs using 3-Tier action model."""
    if not context_docs:
        return {
            "grounded": False,
            "groundedness_score": 0.0,
            "level": "LOW",
            "recommended_action": "ESCALATE",
            "reason": "No context documents provided for groundedness check",
        }

    doc_text = "\n".join([doc.get("content", "") for doc in context_docs]).lower()
    answer_words = [w for w in re.findall(r"\w+", answer.lower()) if len(w) > 4]

    if not answer_words:
        return {
            "grounded": True,
            "groundedness_score": 1.0,
            "level": "HIGH",
            "recommended_action": "AUTO_RESPOND",
            "reason": "Empty or short answer",
        }

    matched = sum(1 for word in answer_words if word in doc_text)
    score = round(matched / len(answer_words), 2)
    
    if score >= 0.75:
        level = "HIGH"
        recommended_action = "AUTO_RESPOND"
        grounded = True
    elif score >= 0.50:
        level = "MEDIUM"
        recommended_action = "ASK_CLARIFICATION"
        grounded = True
    else:
        level = "LOW"
        recommended_action = "ESCALATE"
        grounded = False

    return {
        "grounded": grounded,
        "groundedness_score": score,
        "level": level,
        "recommended_action": recommended_action,
        "citations": [doc.get("doc_id", doc.get("id", "KB-DOC")) for doc in context_docs],
        "reason": f"Groundedness score {score} (Level: {level}, Action: {recommended_action})",
    }


def content_filter(text: str) -> Dict[str, Any]:
    """Main output content filter function."""
    redaction_res = redact_secrets_and_pii(text)
    mod_res = check_openai_moderation(text)

    safe = redaction_res["safe"] and not mod_res.get("flagged", False)

    return {
        "safe": safe,
        "issues": redaction_res["issues"] + mod_res.get("categories", []),
        "redacted": redaction_res["redacted"],
        "severity": redaction_res["severity"],
    }


if __name__ == "__main__":
    print("Testing Output Guardrails...")
    sample = "My database is mysql://root:secret123@10.0.0.5/db and phone is 0912345678"
    print("Original:", sample)
    print("Redacted:", redact_secrets_and_pii(sample))
