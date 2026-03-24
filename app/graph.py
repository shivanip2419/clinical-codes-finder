import os
import json
from typing import List
from openai import OpenAI

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
    query = state["query"]
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    systems = []
    confidence = 0.5
    
    if api_key:
        client = OpenAI(api_key=api_key)
        prompt = f"""
Analyze this clinical query: "{query}"

Return a JSON object with:
1. "systems": A list of relevant databases (choose exactly from: ICD10CM, LOINC, RXTERMS, HCPCS, UCUM, HPO).
2. "confidence": A float from 0.0 to 1.0 indicating how confident you are in this mapping.

Only output valid JSON, no markdown formatting.
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            text = response.choices[0].message.content.strip()
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            
            data = json.loads(text.strip())
            extracted_sys = data.get("systems", [])
            valid = {"ICD10CM", "LOINC", "RXTERMS", "HCPCS", "UCUM", "HPO"}
            systems = [s for s in extracted_sys if s in valid]
            confidence = float(data.get("confidence", 0.5))
        except Exception:
            systems = infer_systems(query)
    else:
        systems = infer_systems(query)
        
    if not systems:
        systems = ["ICD10CM", "LOINC", "RXTERMS"]

    state["systems"] = systems
    state["confidence"] = confidence
    state["iteration"] = 0
    state["trace"] = {"systems_selected": systems, "confidence": confidence}
    return state


def plan_node(state: AgentState) -> AgentState:
    state["search_terms"] = build_search_terms(state["query"], state["systems"])
    conf = state.get("confidence", 0.5)
    
    # Dynamic thresholds based on AI certainty
    if conf >= 0.85:
        state["max_per_system"] = 3
    else:
        state["max_per_system"] = 10
        
    state["trace"]["max_per_system"] = state["max_per_system"]
    return state


def call_tools_node(state: AgentState) -> AgentState:
    all_items = []
    calls_made = 0
    limit = state.get("max_per_system", 5)
    fetch_limit = limit + 7
    
    for system in state["systems"]:
        term = state["search_terms"].get(system)
        if not term: 
            continue
        try:
            items = search_system(system, term, max_list=fetch_limit)
            all_items.extend(items)
            calls_made += 1
        except Exception:
            continue
            
    grouped = group_by_system(all_items)
    for system, items in grouped.items():
        grouped[system] = rank_results(state["query"], items, top_k=limit)
        
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
