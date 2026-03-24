from typing import Literal

from app.state import AgentState


def should_continue(state: AgentState) -> Literal["sanitize", "refine"]:
    """
    Evaluates if the current raw_results are sufficient.
    If yes or if we've hit the max iteration limit, proceed to sanitize.
    If no (e.g., results are empty) and we can still loop, return 'refine'.
    """
    iteration = state.get("iteration", 0)
    MAX_ITERATIONS = 2
    
    if iteration >= MAX_ITERATIONS:
        return "sanitize"
        
    systems = state.get("systems", [])
    raw_results = state.get("raw_results", {})
    
    # Did any of the expected systems fail to return results?
    has_missing_system = any(
        sys in systems and not raw_results.get(sys)
        for sys in systems
    )
    
    if has_missing_system:
        return "refine"
        
    return "sanitize"
