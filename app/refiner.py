import os
import json

from openai import OpenAI

from app.state import AgentState


def refine_node(state: AgentState) -> AgentState:
    """
    Called when results are completely empty or poor.
    Uses LLM to suggest broader or alternate search terms.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    # Increment iteration counter
    state["iteration"] = state.get("iteration", 0) + 1
    
    if not api_key:
        return state
        
    client = OpenAI(api_key=api_key)
    
    query = state.get("query", "")
    systems = state.get("systems", [])
    old_terms = state.get("search_terms", {})
    
    prompt = f"""
You are an expert clinical coding librarian. A user searched for "{query}" across systems: {systems}.
The previous search terms we tried were: {old_terms}.
They returned ZERO matching results from the Clinical Tables API.

Create NEW search terms that are simpler, broader, or correct any spelling mistakes.
For example, if the query was "metastatic breast cancer stage 4 fast spreading", a good broad term is "breast cancer".

Return ONLY a JSON dictionary mapping the clinical system name to the new search term string.
Do not wrap it in markdown block. Just standard JSON output.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = response.choices[0].message.content.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        new_terms = json.loads(text.strip())
        
        for sys in systems:
            if sys in new_terms:
                state["search_terms"][sys] = new_terms[sys]
                
        # Keep a trace logic
        if "refinements" not in state["trace"]:
            state["trace"]["refinements"] = []
        state["trace"]["refinements"].append(new_terms)
        
    except Exception as e:
        print(f"Refinement error: {e}")
        pass
        
    return state
