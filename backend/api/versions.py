"""
backend/api/versions.py

GET /artifact/{artifact_id}              - current artifact metadata
GET /artifact/{artifact_id}/versions     - full version history
GET /artifact/{artifact_id}/download     - download a specific (or latest) version
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.services import artifact_store
from backend.services.artifact_store import ArtifactNotFoundError

router = APIRouter(prefix="/artifact", tags=["versions"])


class VersionInfo(BaseModel):
    version: int
    file_path: str
    change_request: str | None = None


class ArtifactInfo(BaseModel):
    artifact_id: str
    artifact_type: str
    current_version: int
    versions: list[VersionInfo]


@router.get("/{artifact_id}", response_model=ArtifactInfo)
def get_artifact(artifact_id: str) -> ArtifactInfo:
    meta = artifact_store.load_meta(artifact_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"No artifact found for id '{artifact_id}'")
    return ArtifactInfo(
        artifact_id=artifact_id,
        artifact_type=meta["artifact_type"],
        current_version=meta["current_version"],
        versions=[VersionInfo(**v) for v in meta["versions"]],
    )


@router.get("/{artifact_id}/versions", response_model=list[VersionInfo])
def get_versions(artifact_id: str) -> list[VersionInfo]:
    try:
        versions = artifact_store.list_versions(artifact_id)
    except ArtifactNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [VersionInfo(**v) for v in versions]


@router.get("/{artifact_id}/download")
def download_version(artifact_id: str, version: int | None = None):
    meta = artifact_store.load_meta(artifact_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"No artifact found for id '{artifact_id}'")

    target_version = version or meta["current_version"]
    matches = [v for v in meta["versions"] if v["version"] == target_version]
    if not matches:
        raise HTTPException(status_code=404, detail=f"Version {target_version} not found for artifact '{artifact_id}'")

    from pathlib import Path
    file_path = Path(matches[0]["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File for version {target_version} is missing on disk")

    return FileResponse(str(file_path), filename=file_path.name)
