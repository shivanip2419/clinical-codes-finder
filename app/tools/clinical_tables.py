import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import httpx

from app.models import CodeResult, SystemName


API_URLS: Dict[SystemName, str] = {
    "ICD10CM": "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search",
    "LOINC": "https://clinicaltables.nlm.nih.gov/api/loinc_items/v3/search",
    "RXTERMS": "https://clinicaltables.nlm.nih.gov/api/rxterms/v3/search",
    "HCPCS": "https://clinicaltables.nlm.nih.gov/api/hcpcs/v3/search",
    "UCUM": "https://clinicaltables.nlm.nih.gov/api/ucum/v3/search",
    "HPO": "https://clinicaltables.nlm.nih.gov/api/hpo/v3/search",
}

# Optional query params to request richer display text.
# If a variant fails for an endpoint, we fall back gracefully.
SYSTEM_PARAM_VARIANTS: Dict[SystemName, List[Dict[str, str]]] = {
    "ICD10CM": [
        {"df": "name"},
        {"df": "code,name"},
    ],
    "HCPCS": [
        {"df": "long_description"},
        {"df": "short_description"},
        {"df": "code,long_description"},
    ],
    "LOINC": [
        {"df": "LONG_COMMON_NAME"},
    ],
    "RXTERMS": [],
    "UCUM": [],
    "HPO": [
        {"df": "name"},
        {"df": "label"},
        {"df": "code,name"},
    ],
}


def _safe_text(value: object) -> str:
    return str(value) if value is not None else ""


def _to_display(value: Any) -> str:
    def _looks_like_code(text: str) -> bool:
        t = text.strip()
        if not t:
            return False
        return bool(
            re.match(r"^[A-Z][0-9]{2,}(?:\.[0-9A-Z]+)?$", t, flags=re.IGNORECASE)
            or re.match(r"^[A-Z]{2,}:[0-9A-Z]+$", t, flags=re.IGNORECASE)
            or re.match(r"^[0-9]+-[0-9]+$", t)
        )

    if isinstance(value, list):
        if not value:
            return ""
        text_items = [_safe_text(v).strip() for v in value if _safe_text(v).strip()]
        if not text_items:
            return ""
        # Prefer human-readable description over code-like tokens.
        for item in text_items:
            if not _looks_like_code(item):
                return item
        return text_items[0]
    return _safe_text(value)


def _normalize_term_for_system(system: SystemName, term: str) -> str:
    normalized = term.strip().lower()
    if system == "RXTERMS":
        # Drop dose units and forms to improve medication name recall.
        normalized = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu)\b", " ", normalized)
        normalized = re.sub(r"\b(tablet|capsule|tab|cap|solution|syrup)\b", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
    if system == "ICD10CM":
        # "diabetes" is often indexed under "diabetes mellitus"
        if normalized == "diabetes":
            normalized = "diabetes mellitus"
    return normalized


def _extract_results(system: SystemName, payload: Any) -> List[CodeResult]:
    # ClinicalTables responses are not perfectly consistent across systems.
    # This function tries common list layouts and falls back to heuristics.
    def _extract_from_item(item: Any) -> Tuple[str, str]:
        # dict row
        if isinstance(item, Mapping):
            code = (
                item.get("code")
                or item.get("id")
                or item.get("icd10Code")
                or item.get("icd10cmCode")
                or item.get("ICD10CM")
                or item.get("rxtermsCode")
                or item.get("hcpcsCode")
                or item.get("loincCode")
            )
            display = (
                item.get("display")
                or item.get("name")
                or item.get("description")
                or item.get("title")
                or item.get("term")
            )
            code_str = _safe_text(code)
            display_str = _safe_text(display)

            # If we didn't find code via keys, try any string value that "looks like" a code.
            if system == "ICD10CM" and (not code_str or code_str == "0"):
                for v in item.values():
                    if isinstance(v, str) and re.search(r"[A-TV-Z]\s*\d", v, flags=re.IGNORECASE):
                        code_str = v.strip()
                        break
            return (code_str, display_str)

        # row-like list/tuple
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
            row = list(item)
            code = _safe_text(row[0]) if row else ""
            display = _safe_text(row[1]) if len(row) > 1 else ""
            if system == "ICD10CM":
                # Sometimes the row comes as [display, code].
                if (not re.search(r"[A-TV-Z]\s*\d", code, flags=re.IGNORECASE)) and re.search(
                    r"[A-TV-Z]\s*\d", display, flags=re.IGNORECASE
                ):
                    code, display = display, code
            return (code, display)

        # flat string
        s = _safe_text(item)
        return (s, "")

    def _extract_from_code_list(code_list: List[Any]) -> List[CodeResult]:
        def _is_valid_code_for_system(code_str: str) -> bool:
            c = code_str.strip()
            if not c or c == "0":
                return False
            if system == "ICD10CM":
                # ClinicalTables sometimes returns codes with minor formatting differences.
                # We accept anything that looks like ICD-10-CM: a letter followed by digits (optionally with dots).
                return bool(re.search(r"[A-TV-Z]\s*\d", c, flags=re.IGNORECASE))
            # For other systems, keep it permissive for now.
            return True

        results: List[CodeResult] = []
        for item in code_list[:100]:
            code, display = _extract_from_item(item)
            if not code:
                continue
            if not _is_valid_code_for_system(code):
                continue
            if not display:
                display = code
            results.append(
                CodeResult(
                    system=system,
                    code=code,
                    display=display,
                    evidence=f"Retrieved from {system} Clinical Tables API",
                )
            )
        return results

    def _extract_from_standard_shape(list_payload: List[Any]) -> List[CodeResult]:
        # Common ClinicalTables shape:
        # [total, codes[], extra_fields?, display[]]
        if len(list_payload) < 2 or not isinstance(list_payload[1], list):
            return []
        code_list = list_payload[1]
        if not code_list:
            return []

        display_list: List[Any] = []
        if len(list_payload) > 3 and isinstance(list_payload[3], list):
            display_list = list_payload[3]

        extra_fields: Mapping[str, Any] = {}
        if len(list_payload) > 2 and isinstance(list_payload[2], Mapping):
            extra_fields = list_payload[2]

        base_results = _extract_from_code_list(code_list)
        if not base_results:
            return []

        code_to_index = {_safe_text(code): idx for idx, code in enumerate(code_list)}
        for result in base_results:
            idx = code_to_index.get(result.code)
            if idx is None:
                continue

            # 1) Prefer display array value when available.
            if idx < len(display_list):
                display_from_list = _to_display(display_list[idx]).strip()
                if display_from_list and display_from_list != result.code:
                    result.display = display_from_list
                    continue

            # 2) Fall back to first non-empty descriptive extra field.
            for field_values in extra_fields.values():
                if isinstance(field_values, list) and idx < len(field_values):
                    candidate = _to_display(field_values[idx]).strip()
                    if candidate and candidate != result.code:
                        result.display = candidate
                        break

        return base_results

    def _extract_from_mapping(m: Mapping[str, Any]) -> List[CodeResult]:
        for v in m.values():
            if isinstance(v, list) and v:
                results = _extract_from_code_list(v)
                if results:
                    return results
        return []

    # Dict payload: pick the first list-ish field that yields results.
    if isinstance(payload, Mapping):
        return _extract_from_mapping(payload)

    # List payload: scan all elements for nested "code lists" or mappings.
    if not isinstance(payload, list) or not payload:
        return []

    # Try canonical ClinicalTables layout first to preserve human-readable display text.
    standard_results = _extract_from_standard_shape(payload)
    if standard_results:
        return standard_results

    # First: shallow scan.
    for element in payload:
        if isinstance(element, Mapping):
            results = _extract_from_mapping(element)
            if results:
                return results
        if isinstance(element, list) and element:
            results = _extract_from_code_list(element)
            if results:
                return results

    # Second: recursive scan for nested lists anywhere in the payload.
    def _collect_lists(obj: Any, remaining_depth: int) -> List[List[Any]]:
        if remaining_depth <= 0:
            return []
        out: List[List[Any]] = []
        if isinstance(obj, list):
            if obj:
                out.append(obj)
            for it in obj:
                out.extend(_collect_lists(it, remaining_depth - 1))
        elif isinstance(obj, Mapping):
            for v in obj.values():
                out.extend(_collect_lists(v, remaining_depth - 1))
        return out

    nested_lists = _collect_lists(payload, remaining_depth=5)[:30]
    for code_list in nested_lists:
        results = _extract_from_code_list(code_list)
        if results:
            return results

    return []


def _dedupe_by_code(items: List[CodeResult]) -> List[CodeResult]:
    deduped: Dict[str, CodeResult] = {}
    for item in items:
        key = f"{item.system}:{item.code}".lower()
        if key not in deduped:
            deduped[key] = item
    return list(deduped.values())


def search_system(system: SystemName, term: str, max_list: int = 10) -> List[CodeResult]:
    url = API_URLS[system]
    normalized = _normalize_term_for_system(system, term)
    candidate_terms = [term]
    if system == "ICD10CM":
        q = term.strip().lower()
        if "diabetes" in q:
            # ICD-10-CM diabetes codes are spread across E10-E14.
            # The Clinical Tables search endpoint appears more reliable with code prefixes.
            candidate_terms.extend(["E10", "E11", "E12", "E13", "E14"])
        if "tuberculosis" in q or re.search(r"\btb\b", q):
            # ICD-10-CM tuberculosis codes are grouped primarily in A15-A19.
            candidate_terms.extend(["A15", "A16", "A17", "A18", "A19"])
    if normalized and normalized != term:
        candidate_terms.append(normalized)

    # De-dup while preserving order (case-insensitive).
    seen: set[str] = set()
    deduped: List[str] = []
    for t in candidate_terms:
        key = t.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(t)
    candidate_terms = deduped

    collected: List[CodeResult] = []
    with httpx.Client(timeout=15.0) as client:
        for candidate in candidate_terms:
            base_params = {"terms": candidate, "maxList": max_list}
            param_variants = SYSTEM_PARAM_VARIANTS.get(system, [])
            # Try richer display variants first, then plain request.
            for variant in [*param_variants, {}]:
                params = {**base_params, **variant}
                try:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                except Exception:
                    # Some endpoints reject unknown df fields; keep trying fallbacks.
                    continue

                payload = response.json()
                parsed = _extract_results(system, payload)
                if parsed:
                    collected.extend(parsed)
                    break
            if collected:
                break

    return _dedupe_by_code(collected)
