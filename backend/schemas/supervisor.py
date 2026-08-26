"""
backend/schemas/supervisor.py
"""
from typing import Optional
from pydantic import BaseModel, Field


class ExecutionPlan(BaseModel):
    """
    Structured interpretation of the user's request, produced by the
    Supervisor Agent. This mirrors the example in the assignment:
    the supervisor inspects intent + available files and decides which
    downstream agents are actually needed, rather than always running
    every agent on every request.
    """
    intent: str                                   # e.g. "generate_artifacts", "research_only", "analyze_only"
    needs_document_analysis: bool = False
    needs_ppt_analysis: bool = False
    needs_web_research: bool = False
    needs_rag: bool = False
    generate_docx: bool = False
    generate_pptx: bool = False
    slide_count: Optional[int] = None
    requires_validation: bool = True
    research_query: Optional[str] = None
    reasoning: str = ""                            # short explanation of why this plan was chosen


class AgentCallRecord(BaseModel):
    agent: str
    status: str                                    # "success" | "skipped" | "failed"
    detail: str = ""


class OrchestrationResult(BaseModel):
    user_request: str
    plan: ExecutionPlan
    agent_calls: list[AgentCallRecord] = Field(default_factory=list)
    document_analysis: Optional[dict] = None
    ppt_analysis: Optional[dict] = None
    research: Optional[dict] = None
    rag_results: Optional[dict] = None
    citation_summary: dict[str, dict] = Field(default_factory=dict)
    next_step_note: str = ""
    warnings: list[str] = Field(default_factory=list)
    trace_id: Optional[str] = None
    generated_docx_artifact_id: Optional[str] = None
    generated_pptx_artifact_id: Optional[str] = None
    docx_validation_status: Optional[str] = None
    pptx_validation_status: Optional[str] = None
