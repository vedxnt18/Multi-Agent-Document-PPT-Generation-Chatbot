"""
backend/schemas/editing.py
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


EditOperation = Literal["add_section", "remove_section", "modify_section", "condense", "unsupported"]


class EditInstruction(BaseModel):
    operation: EditOperation
    target_heading: Optional[str] = None      # for remove_section / modify_section
    new_heading: Optional[str] = None          # for add_section
    new_paragraphs: list[str] = Field(default_factory=list)
    new_bullet_points: list[str] = Field(default_factory=list)
    reasoning: str = ""


class EditResult(BaseModel):
    artifact_id: str
    new_version: int
    file_path: str
    instruction: EditInstruction
    change_summary: str
    validation_status: str
