from fastapi import APIRouter

from app.models import FindCodesRequest, FindCodesResponse
from app.services.code_finder import run_code_finder

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.post("/find-codes", response_model=FindCodesResponse)
def find_codes(request: FindCodesRequest) -> FindCodesResponse:
    final_state = run_code_finder(request.query)
    return FindCodesResponse(
        query=request.query,
        results_by_system=final_state["raw_results"],
        summary=final_state["summary"],
        trace=final_state["trace"],
    )
