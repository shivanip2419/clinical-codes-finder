from typing import Dict, List

from app.models import SystemName
from app.normalization import normalize_query_text


def build_search_terms(query: str, systems: List[SystemName]) -> Dict[SystemName, str]:
    query = normalize_query_text(query)
    return {system: query for system in systems}
