import re
from typing import Dict, List

from app.models import CodeResult


_PII_PATTERNS = [
    # Email
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    # US phone number variants
    (re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
    # SSN
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    # Date-like strings (DOB patterns)
    (re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"), "[REDACTED_DATE]"),
    # MRN-style labels
    (re.compile(r"\b(?:MRN|Medical Record Number)\s*[:#]?\s*[A-Za-z0-9-]+\b", re.IGNORECASE), "[REDACTED_MRN]"),
    # Patient name labels
    (re.compile(r"\b(?:patient|pt)\s*name\s*[:#]?\s*[A-Za-z][A-Za-z' -]{1,60}\b", re.IGNORECASE), "[REDACTED_NAME]"),
]


def redact_text(text: str) -> str:
    redacted = text
    for pattern, replacement in _PII_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_results(grouped: Dict[str, List[CodeResult]]) -> Dict[str, List[CodeResult]]:
    sanitized: Dict[str, List[CodeResult]] = {}
    for system, items in grouped.items():
        sanitized_items: List[CodeResult] = []
        for item in items:
            redacted_metadata = {k: redact_text(v) for k, v in item.metadata.items()}
            sanitized_items.append(
                CodeResult(
                    system=item.system,
                    code=item.code,
                    display=redact_text(item.display),
                    score=item.score,
                    evidence=redact_text(item.evidence),
                    metadata=redacted_metadata,
                )
            )
        sanitized[system] = sanitized_items
    return sanitized
