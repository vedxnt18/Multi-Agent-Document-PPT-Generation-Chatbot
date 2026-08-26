"""
backend/schemas/validation.py
"""
from typing import Literal
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    status: Literal["PASS", "FAIL"]
    artifact_type: str            # "docx" | "pptx"
    file_path: str
    issues: list[str] = Field(default_factory=list)     # cause a FAIL
    warnings: list[str] = Field(default_factory=list)    # noteworthy but not fatal
