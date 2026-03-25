from typing import Dict, List

from app.config import default_initial_state
from app.graph import build_graph
from app.models import CodeResult

_COMPILED_GRAPH = build_graph()


async def run_code_finder(query: str) -> Dict[str, object]:
    state = default_initial_state(query)
    final_state = await _COMPILED_GRAPH.ainvoke(state)
    return final_state


def extract_results_by_system(final_state: Dict[str, object]) -> Dict[str, List[CodeResult]]:
    raw = final_state.get("raw_results", {})
    return raw if isinstance(raw, dict) else {}
