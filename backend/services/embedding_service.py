"""
backend/services/embedding_service.py

Local embedding generation via fastembed (ONNX runtime), which runs
Sentence-Transformer-family models without requiring PyTorch. No API key
needed. Model is downloaded once (cached under ~/.cache/fastembed) on
first use.

Note on model choice: fastembed's default "BAAI/bge-small-en-v1.5" is used
rather than sentence-transformers/all-MiniLM-L6-v2 (which isn't bundled
with fastembed) — both are small, fast, general-purpose English embedding
models in the same weight class (~130MB, 384-dim). This is documented in
the README's Embeddings section.
"""
import logging
from functools import lru_cache
from typing import List

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384


class EmbeddingService:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None

    def _ensure_loaded(self):
        if self._model is None:
            from fastembed import TextEmbedding
            logger.info(f"Loading embedding model '{self.model_name}' (first call downloads/caches it)...")
            self._model = TextEmbedding(model_name=self.model_name)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts. Returns one vector per input text, same order."""
        if not texts:
            return []
        self._ensure_loaded()
        embeddings = list(self._model.embed(texts))
        return [vec.tolist() for vec in embeddings]

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        return self.embed_texts([text])[0]

    @property
    def dimension(self) -> int:
        return EMBEDDING_DIM


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    from backend.config import settings
    return EmbeddingService(model_name=DEFAULT_MODEL if not settings.embedding_model else DEFAULT_MODEL)
