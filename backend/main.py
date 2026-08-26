"""
backend/main.py

FastAPI application entrypoint. Run with:
    uvicorn backend.main:app --reload --port 8000
(from the project root, with the venv activated)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.api import upload, ingest, analyze, rag, research, chat, generate, validate, edit, versions, convert, trace

app = FastAPI(
    title="Multi-Agent Document & PPT Generation Chatbot",
    description="Enterprise-grade multi-agent AI chatbot backend for document/PPT analysis, generation, RAG, and conversational editing.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(ingest.router)
app.include_router(analyze.router)
app.include_router(rag.router)
app.include_router(research.router)
app.include_router(chat.router)
app.include_router(generate.router)
app.include_router(validate.router)
app.include_router(edit.router)
app.include_router(versions.router)
app.include_router(convert.router)
app.include_router(trace.router)


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "llm_provider": settings.llm_provider,
        "vector_store": settings.vector_store,
        "web_search_provider": settings.web_search_provider,
    }
