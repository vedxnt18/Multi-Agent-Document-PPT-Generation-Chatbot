"""
backend/api/chat.py

POST /chat
Entry point for a user's natural-language request plus any relevant
uploaded file_ids. Runs the full Supervisor orchestration pipeline
(Phase 7) and returns the aggregated result.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.agents.supervisor import orchestrate
from backend.schemas.supervisor import OrchestrationResult

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    file_ids: list[str] = Field(default_factory=list)


@router.post("", response_model=OrchestrationResult)
def chat(request: ChatRequest) -> OrchestrationResult:
    return orchestrate(request.message, request.file_ids)
