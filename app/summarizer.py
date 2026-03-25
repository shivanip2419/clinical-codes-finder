import os
from typing import Dict, List

from openai import AsyncOpenAI

from app.models import CodeResult


def _fallback_summary(query: str, grouped: Dict[str, List[CodeResult]]) -> str:
    if not grouped:
        return f"No strong code matches were found for '{query}' in this run."
    systems = ", ".join(grouped.keys())
    return f"Top matches for '{query}' were found in: {systems}."


async def summarize_results(query: str, grouped: Dict[str, List[CodeResult]]) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return _fallback_summary(query, grouped)

    client = AsyncOpenAI(api_key=api_key)
    compact = {
        system: [
            {"code": item.code, "display": item.display, "score": item.score}
            for item in items[:3]
        ]
        for system, items in grouped.items()
    }
    prompt = (
        "You are a clinical coding assistant. Summarize results in 3-4 lines, "
        "mention strongest systems and uncertainty briefly.\n"
        f"Query: {query}\nResults: {compact}"
    )
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        text = response.choices[0].message.content.strip()
        return text or _fallback_summary(query, grouped)
    except Exception:
        # Network/proxy/API errors should not break the endpoint.
        return _fallback_summary(query, grouped)
