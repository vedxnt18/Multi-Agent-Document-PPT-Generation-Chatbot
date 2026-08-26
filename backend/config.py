"""
backend/config.py

Central application configuration. All other modules should import `settings`
from here rather than reading os.environ directly, so we have exactly one
place that knows how env vars map to config values.
"""
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = two levels up from this file (backend/config.py -> project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # --- App ---
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # --- CORS ---
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"

    # --- Uploads ---
    max_upload_size_mb: int = 25
    allowed_upload_extensions: str = ".pdf,.docx,.pptx,.png,.jpg,.jpeg"

    # --- Storage paths (relative to project root) ---
    upload_dir: str = "data/uploads"
    template_dir: str = "data/templates"
    generated_dir: str = "data/generated"
    version_dir: str = "data/versions"
    knowledge_base_dir: str = "data/knowledge_base"
    sqlite_db_path: str = "data/app.db"

    # --- LLM (Phase 4) ---
    llm_provider: str = "mock"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    groq_api_key: str = ""

    # --- Embeddings (Phase 5) ---
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- Vector store (Phase 5) ---
    vector_store: str = "faiss"
    pinecone_api_key: str = ""
    pinecone_environment: str = ""
    pinecone_index_name: str = "docgen-multiagent"

    # --- Web search (Phase 6) ---
    web_search_provider: str = "mock"
    tavily_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Derived helpers ---
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [e.strip().lower() for e in self.allowed_upload_extensions.split(",") if e.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def resolve_path(self, relative: str) -> Path:
        """Resolve a relative data path against the project root, creating it if missing."""
        p = PROJECT_ROOT / relative
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
