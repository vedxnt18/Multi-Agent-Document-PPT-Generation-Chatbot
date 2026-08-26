"""
backend/api/trace.py

GET /trace/{trace_id}   - full trace record for a prior /chat orchestration
GET /trace              - recent traces (developer/admin panel listing)
"""
from fastapi import APIRouter, HTTPException

from backend.services import trace_service

router = APIRouter(prefix="/trace", tags=["trace"])


@router.get("")
def list_recent_traces(limit: int = 50):
    return trace_service.list_traces(limit=limit)


@router.get("/{trace_id}")
def get_trace(trace_id: str):
    trace = trace_service.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"No trace found for id '{trace_id}'")
    return trace
