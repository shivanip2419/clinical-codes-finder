import re
from difflib import get_close_matches
from typing import List, Set

# Controlled vocabulary for typo normalization. Keep this focused to avoid
# over-correcting domain-specific terms.
KNOWN_TERMS: Set[str] = {
    "blood",
    "sugar",
    "glucose",
    "test",
    "panel",
    "lab",
    "a1c",
    "metformin",
    "insulin",
    "tablet",
    "capsule",
    "wheelchair",
    "prosthetic",
    "supply",
    "device",
    "ataxia",
    "phenotype",
    "symptom",
    "diabetes",
    "mellitus",
    "tuberculosis",
    "disease",
    "diagnosis",
    "mg",
    "mcg",
    "mmol/l",
    "mg/dl",
    "unit",
    "tb",
}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9/.\-]+|[^a-z0-9/.\-\s]", text.lower())


def _should_keep(token: str) -> bool:
    # Preserve numeric/code-like tokens and short abbreviations.
    if re.match(r"^[a-z]\d+(\.\d+)?$", token):  # e.g., e11.9
        return True
    if re.match(r"^\d+([./-]\d+)?$", token):
        return True
    if len(token) <= 2:
        return True
    return False


def normalize_query_text(query: str) -> str:
    tokens = _tokenize(query)
    normalized: List[str] = []
    for tok in tokens:
        if not re.match(r"^[a-z0-9/.\-]+$", tok):
            normalized.append(tok)
            continue

        if tok in KNOWN_TERMS or _should_keep(tok):
            normalized.append(tok)
            continue

        match = get_close_matches(tok, KNOWN_TERMS, n=1, cutoff=0.86)
        normalized.append(match[0] if match else tok)

    # rebuild with spaces around word tokens only
    out = " ".join(t for t in normalized if t.strip())
    out = re.sub(r"\s+", " ", out).strip()
    return out
