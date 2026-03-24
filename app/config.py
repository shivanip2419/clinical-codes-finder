from typing import Any, Dict, List

CHAT_UI_CONFIG: Dict[str, Any] = {
    "maxPerSystem": 5,
    "supportedSystems": ["ICD-10-CM", "LOINC", "RxTerms", "HCPCS", "UCUM", "HPO"],
    "sampleQueries": [
        "diabetes",
        "glucose test",
        "metformin 500 mg",
        "wheelchair",
        "mg/dL",
        "ataxia",
        "tuberculosis",
    ],
}


def default_initial_state(query: str) -> Dict[str, Any]:
    return {
        "query": query,
        "systems": [],
        "search_terms": {},
        "raw_results": {},
        "summary": "",
        "trace": {},
    }
