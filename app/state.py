from typing import Dict, List, TypedDict

from app.models import CodeResult, SystemName


class AgentState(TypedDict):
    query: str
    systems: List[SystemName]
    search_terms: Dict[SystemName, str]
    raw_results: Dict[str, List[CodeResult]]
    summary: str
    trace: Dict[str, object]
    iteration: int
    confidence: float
    max_per_system: int
