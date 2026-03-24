from typing import List

from langgraph.graph import END, StateGraph

from app.intent import infer_systems
from app.planner import build_search_terms
from app.privacy import redact_results
from app.ranker import rank_results
from app.state import AgentState
from app.summarizer import summarize_results
from app.tools.clinical_tables import search_system
from app.tools.mappers import group_by_system
from app.evaluator import should_continue
from app.refiner import refine_node


def intent_node(state: AgentState) -> AgentState:
    systems = infer_systems(state["query"])
    state["systems"] = systems
    state["trace"] = {"systems_selected": systems}
    return state


def plan_node(state: AgentState) -> AgentState:
    state["search_terms"] = build_search_terms(state["query"], state["systems"])
    return state


def call_tools_node(state: AgentState) -> AgentState:
    all_items = []
    calls_made = 0
    for system in state["systems"]:
        term = state["search_terms"][system]
        try:
            items = search_system(system, term, max_list=12)
            all_items.extend(items)
            calls_made += 1
        except Exception:
            continue
    grouped = group_by_system(all_items)
    for system, items in grouped.items():
        grouped[system] = rank_results(state["query"], items, top_k=5)
    state["raw_results"] = grouped
    state["trace"]["calls_made"] = calls_made
    return state


def summarize_node(state: AgentState) -> AgentState:
    state["summary"] = summarize_results(state["query"], state["raw_results"])
    return state


def sanitize_node(state: AgentState) -> AgentState:
    # Ensure potentially sensitive text is masked before downstream phases.
    state["raw_results"] = redact_results(state["raw_results"])
    return state


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("intent", intent_node)
    graph.add_node("plan", plan_node)
    graph.add_node("call_tools", call_tools_node)
    graph.add_node("refine", refine_node)
    graph.add_node("sanitize", sanitize_node)
    graph.add_node("summarize", summarize_node)

    graph.set_entry_point("intent")
    graph.add_edge("intent", "plan")
    graph.add_edge("plan", "call_tools")
    
    # Conditional edge after tool execution
    graph.add_conditional_edges(
        "call_tools",
        should_continue,
        {
            "sanitize": "sanitize",
            "refine": "refine"
        }
    )
    
    # Refine loops back to call_tools
    graph.add_edge("refine", "call_tools")
    
    graph.add_edge("sanitize", "summarize")
    graph.add_edge("summarize", END)
    return graph.compile()
