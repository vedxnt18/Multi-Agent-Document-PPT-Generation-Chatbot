"""
backend/api/edit.py

POST /artifact/{artifact_id}/edit
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.conversational_editor import edit_artifact
from backend.services.artifact_store import ArtifactNotFoundError
from backend.schemas.editing import EditResult

router = APIRouter(prefix="/artifact", tags=["editing"])


class EditRequest(BaseModel):
    request: str


@router.post("/{artifact_id}/edit", response_model=EditResult)
def edit_artifact_endpoint(artifact_id: str, req: EditRequest) -> EditResult:
    try:
        return edit_artifact(artifact_id, req.request)
    except ArtifactNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
