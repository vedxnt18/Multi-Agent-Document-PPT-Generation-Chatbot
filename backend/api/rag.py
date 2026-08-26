"""
backend/api/rag.py

POST /rag/index/{file_id}   - extract + chunk + embed + upsert an uploaded file
POST /rag/query             - embed a query, retrieve top-k chunks with citations
"""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.api.ingest import _find_uploaded_file
from backend.services.extraction_service import extract_file
from backend.agents.rag_agent import ingest_document, query_knowledge_base
from backend.schemas.rag import RAGIngestResponse, RAGQueryResponse

router = APIRouter(prefix="/rag", tags=["rag"])


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/index/{file_id}", response_model=RAGIngestResponse)
def index_file(file_id: str) -> RAGIngestResponse:
    file_path = _find_uploaded_file(file_id)
    original_filename = file_path.name.split("_", 1)[1] if "_" in file_path.name else file_path.name
    extraction = extract_file(str(file_path), file_id, original_filename)
    return ingest_document(extraction, document_id=file_id)


@router.post("/query", response_model=RAGQueryResponse)
def query(request: RAGQueryRequest) -> RAGQueryResponse:
    return query_knowledge_base(request.query, top_k=request.top_k)
