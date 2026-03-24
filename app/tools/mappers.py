from typing import Dict, List

from app.models import CodeResult


def group_by_system(results: List[CodeResult]) -> Dict[str, List[CodeResult]]:
    grouped: Dict[str, List[CodeResult]] = {}
    for item in results:
        grouped.setdefault(item.system, []).append(item)
    return grouped
