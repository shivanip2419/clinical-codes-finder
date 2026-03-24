import re
from typing import Dict, List, Set

from app.models import CodeResult


SYNONYMS: Dict[str, Set[str]] = {
    "glucose": {"blood sugar"},
    "blood sugar": {"glucose"},
    "wheelchair": {"mobility chair"},
    "ataxia": {"gait ataxia", "limb ataxia"},
    "diabetes": {"diabetes mellitus"},
    "metformin": {"glucophage"},
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9:/\.-]+", text.lower())


def _expand_query_terms(query: str) -> Set[str]:
    q = _normalize(query)
    terms: Set[str] = {q}
    # Token-level additions
    for tok in _tokens(q):
        terms.add(tok)
        terms.update(SYNONYMS.get(tok, set()))
    # Phrase-level additions
    for base, syns in SYNONYMS.items():
        if base in q:
            terms.update(syns)
    return {t for t in terms if t}


def rank_results(query: str, items: List[CodeResult], top_k: int) -> List[CodeResult]:
    q = _normalize(query)
    expanded_terms = _expand_query_terms(q)
    query_tokens = set(_tokens(q))

    for item in items:
        display = _normalize(item.display)
        code = _normalize(item.code)
        score = 0.15

        # Strong boost for exact phrase in display/code
        if q and q in display:
            score += 0.42
        if q and q in code:
            score += 0.3

        # Synonym/expanded-phrase support
        matched_expanded = sum(1 for term in expanded_terms if term in display or term in code)
        score += min(0.25, matched_expanded * 0.06)

        # Token overlap against display
        display_tokens = set(_tokens(display))
        shared = len(query_tokens & display_tokens)
        if query_tokens:
            score += min(0.25, (shared / len(query_tokens)) * 0.25)

        # Small bonus for medical-looking code patterns
        if re.match(r"^[A-Z][0-9]", item.code):
            score += 0.03
        if ":" in item.code:
            score += 0.02

        item.score = round(min(score, 0.99), 3)
    ranked = sorted(items, key=lambda x: x.score, reverse=True)
    return ranked[:top_k]
