"""
backend/services/artifact_store.py

Minimal artifact persistence. Stores the ContentPlan (as JSON) alongside
each generated file version, so the Conversational Editing Agent has
something to load, modify, and re-save — and so Phase 13 (Versioning) has
a natural place to plug in version history without a rewrite.

This is intentionally simple (JSON files on disk, one per artifact_id)
rather than a database — SQLite for full application state (conversations,
users, etc.) is Phase 13/22's job. This store's only responsibility is
"given an artifact_id, what ContentPlan produced it, and where do new
versions go."

Layout (flat, consistent with the existing data/generated/ convention from
Phase 8/9):
    data/generated/{artifact_id}_v1.docx (or .pptx)
    data/generated/{artifact_id}_v1.plan.json
    data/generated/{artifact_id}_v2.docx
    data/generated/{artifact_id}_v2.plan.json
    data/generated/{artifact_id}.meta.json   <- {"artifact_type", "current_version", "style_spec", "versions": [...]}
"""
import json
import logging
from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.schemas.content_plan import ContentPlan

logger = logging.getLogger(__name__)


class ArtifactNotFoundError(Exception):
    pass


def _generated_dir() -> Path:
    return settings.resolve_path(settings.generated_dir)


def _meta_path(artifact_id: str) -> Path:
    return _generated_dir() / f"{artifact_id}.meta.json"


def save_version(
    artifact_id: str,
    artifact_type: str,
    version: int,
    file_path: str,
    content_plan: ContentPlan,
    style_spec: Optional[dict] = None,
    change_request: Optional[str] = None,
) -> None:
    gen_dir = _generated_dir()
    gen_dir.mkdir(parents=True, exist_ok=True)

    plan_path = gen_dir / f"{artifact_id}_v{version}.plan.json"
    plan_path.write_text(content_plan.model_dump_json(indent=2))

    meta = load_meta(artifact_id) or {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "style_spec": style_spec,
        "versions": [],
    }
    meta["current_version"] = version
    meta["style_spec"] = style_spec if style_spec is not None else meta.get("style_spec")
    meta["versions"].append(
        {
            "version": version,
            "file_path": file_path,
            "plan_path": str(plan_path),
            "change_request": change_request,
        }
    )
    _meta_path(artifact_id).write_text(json.dumps(meta, indent=2))


def load_meta(artifact_id: str) -> Optional[dict]:
    path = _meta_path(artifact_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_latest_content_plan(artifact_id: str) -> ContentPlan:
    meta = load_meta(artifact_id)
    if meta is None:
        raise ArtifactNotFoundError(f"No artifact found for id '{artifact_id}'")
    latest = meta["versions"][-1]
    plan_data = json.loads(Path(latest["plan_path"]).read_text())
    return ContentPlan(**plan_data)


def get_latest_version_number(artifact_id: str) -> int:
    meta = load_meta(artifact_id)
    if meta is None:
        return 0
    return meta["current_version"]


def get_artifact_type(artifact_id: str) -> str:
    meta = load_meta(artifact_id)
    if meta is None:
        raise ArtifactNotFoundError(f"No artifact found for id '{artifact_id}'")
    return meta["artifact_type"]


def get_style_spec(artifact_id: str) -> Optional[dict]:
    meta = load_meta(artifact_id)
    if meta is None:
        return None
    return meta.get("style_spec")


def list_versions(artifact_id: str) -> list[dict]:
    meta = load_meta(artifact_id)
    if meta is None:
        raise ArtifactNotFoundError(f"No artifact found for id '{artifact_id}'")
    return meta["versions"]
