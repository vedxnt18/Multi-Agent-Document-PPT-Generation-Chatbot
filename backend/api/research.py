"""
backend/api/research.py

POST /research
"""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.agents.web_research import research
from backend.schemas.research import ResearchResponse

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    query: str
    max_results: int = 5


@router.post("", response_model=ResearchResponse)
def run_research(request: ResearchRequest) -> ResearchResponse:
    return research(request.query, max_results=request.max_results)
