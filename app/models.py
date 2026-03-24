from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


SystemName = Literal["ICD10CM", "LOINC", "RXTERMS", "HCPCS", "UCUM", "HPO"]


class CodeResult(BaseModel):
    system: SystemName
    code: str
    display: str
    score: float = 0.0
    evidence: str = ""
    metadata: Dict[str, str] = Field(default_factory=dict)


class FindCodesRequest(BaseModel):
    query: str
    max_per_system: int = 5


class FindCodesResponse(BaseModel):
    query: str
    results_by_system: Dict[str, List[CodeResult]]
    summary: str
    trace: Dict[str, object]
    warnings: Optional[List[str]] = None
