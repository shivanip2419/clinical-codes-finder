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
        
    raw_results = state.get("raw_results", {})
    
    # Are there any results at all?
    has_results = any(len(items) > 0 for items in raw_results.values())
    
    if not has_results:
        return "refine"
        
    return "sanitize"
