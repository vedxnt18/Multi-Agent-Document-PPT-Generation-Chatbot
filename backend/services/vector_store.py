"""
backend/services/vector_store.py

Vector store abstraction so the RAG agent never talks to FAISS or Pinecone
directly. `get_vector_store()` returns PineconeStore if PINECONE_API_KEY is
set and reachable, otherwise falls back to FAISSStore with a logged warning
— per the assignment's "Using local vector-store fallback" error-handling
example.

    VectorStore (ABC)
    ├── FAISSStore      - local, in-process, persisted to disk as a pickle+index pair
    └── PineconeStore    - cloud, used when PINECONE_API_KEY is configured
"""
import json
import logging
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorMatch:
    id: str
    score: float
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStoreError(Exception):
    pass


class VectorStore(ABC):
    name: str = "base"

    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        ...

    @abstractmethod
    def query(self, vector: list[float], top_k: int = 5, filter: Optional[dict] = None) -> list[VectorMatch]:
        ...

    @abstractmethod
    def delete_by_document(self, document_id: str) -> None:
        ...


class FAISSStore(VectorStore):
    """
    Local vector store using FAISS for similarity search, with a parallel
    dict for metadata/text (FAISS itself only stores vectors + integer ids).
    Persisted to disk under data/knowledge_base/faiss_index/ so it survives
    process restarts.
    """
    name = "faiss"

    def __init__(self, dimension: int, persist_dir: Optional[Path] = None):
        import faiss

        self._dimension = dimension
        self._persist_dir = persist_dir or settings.resolve_path(settings.knowledge_base_dir) / "faiss_index"
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._persist_dir / "index.faiss"
        self._meta_path = self._persist_dir / "meta.pkl"

        self._records_by_int_id: dict[int, VectorRecord] = {}
        self._id_to_int: dict[str, int] = {}
        self._next_int_id = 0

        if self._index_path.exists() and self._meta_path.exists():
            self._index = faiss.read_index(str(self._index_path))
            with open(self._meta_path, "rb") as f:
                state = pickle.load(f)
                self._records_by_int_id = state["records_by_int_id"]
                self._id_to_int = state["id_to_int"]
                self._next_int_id = state["next_int_id"]
        else:
            # IndexFlatIP over normalized vectors == cosine similarity
            self._index = faiss.IndexIDMap(faiss.IndexFlatIP(dimension))

    def _persist(self) -> None:
        import faiss
        faiss.write_index(self._index, str(self._index_path))
        with open(self._meta_path, "wb") as f:
            pickle.dump(
                {
                    "records_by_int_id": self._records_by_int_id,
                    "id_to_int": self._id_to_int,
                    "next_int_id": self._next_int_id,
                },
                f,
            )

    @staticmethod
    def _normalize(vec: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vec, axis=-1, keepdims=True)
        norm[norm == 0] = 1e-10
        return vec / norm

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        vectors = np.array([r.vector for r in records], dtype=np.float32)
        vectors = self._normalize(vectors)
        int_ids = []
        for r in records:
            if r.id in self._id_to_int:
                int_id = self._id_to_int[r.id]
            else:
                int_id = self._next_int_id
                self._next_int_id += 1
                self._id_to_int[r.id] = int_id
            self._records_by_int_id[int_id] = r
            int_ids.append(int_id)
        self._index.add_with_ids(vectors, np.array(int_ids, dtype=np.int64))
        self._persist()

    def query(self, vector: list[float], top_k: int = 5, filter: Optional[dict] = None) -> list[VectorMatch]:
        if self._index.ntotal == 0:
            return []
        query_vec = self._normalize(np.array([vector], dtype=np.float32))
        scores, int_ids = self._index.search(query_vec, min(top_k * 4 if filter else top_k, self._index.ntotal))

        matches = []
        for score, int_id in zip(scores[0], int_ids[0]):
            if int_id == -1:
                continue
            record = self._records_by_int_id.get(int(int_id))
            if record is None:
                continue
            if filter and not _metadata_matches_filter(record.metadata, filter):
                continue
            matches.append(VectorMatch(id=record.id, score=float(score), text=record.text, metadata=record.metadata))
            if len(matches) >= top_k:
                break
        return matches

    def delete_by_document(self, document_id: str) -> None:
        to_remove = [int_id for int_id, r in self._records_by_int_id.items() if r.metadata.get("document_id") == document_id]
        if not to_remove:
            return
        self._index.remove_ids(np.array(to_remove, dtype=np.int64))
        for int_id in to_remove:
            record = self._records_by_int_id.pop(int_id)
            self._id_to_int.pop(record.id, None)
        self._persist()


def _metadata_matches_filter(metadata: dict, filter: dict) -> bool:
    return all(metadata.get(k) == v for k, v in filter.items())


class PineconeStore(VectorStore):
    """
    Cloud vector store via Pinecone. Requires PINECONE_API_KEY and an index
    name (created automatically if it doesn't exist).
    """
    name = "pinecone"

    def __init__(self, api_key: str, index_name: str, dimension: int):
        if not api_key:
            raise VectorStoreError("PINECONE_API_KEY is not set but VECTOR_STORE=pinecone")
        from pinecone import Pinecone, ServerlessSpec

        self._pc = Pinecone(api_key=api_key)
        self._index_name = index_name
        self._dimension = dimension

        existing = [idx["name"] for idx in self._pc.list_indexes()]
        if index_name not in existing:
            logger.info(f"Creating Pinecone index '{index_name}' (dimension={dimension})...")
            self._pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        self._index = self._pc.Index(index_name)

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        vectors = [
            {
                "id": r.id,
                "values": r.vector,
                "metadata": {**r.metadata, "text": r.text[:40000]},  # Pinecone metadata size limits
            }
            for r in records
        ]
        try:
            self._index.upsert(vectors=vectors)
        except Exception as e:
            raise VectorStoreError(f"Pinecone upsert failed: {e}") from e

    def query(self, vector: list[float], top_k: int = 5, filter: Optional[dict] = None) -> list[VectorMatch]:
        try:
            response = self._index.query(vector=vector, top_k=top_k, include_metadata=True, filter=filter or None)
        except Exception as e:
            raise VectorStoreError(f"Pinecone query failed: {e}") from e

        matches = []
        for m in response.get("matches", []):
            meta = dict(m.get("metadata", {}))
            text = meta.pop("text", "")
            matches.append(VectorMatch(id=m["id"], score=float(m["score"]), text=text, metadata=meta))
        return matches

    def delete_by_document(self, document_id: str) -> None:
        try:
            self._index.delete(filter={"document_id": document_id})
        except Exception as e:
            raise VectorStoreError(f"Pinecone delete failed: {e}") from e


_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    Returns a cached VectorStore based on settings.vector_store. Falls back
    to FAISSStore with a logged warning if Pinecone can't be initialized
    (missing key, network failure), so RAG never hard-crashes.
    """
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    from backend.services.embedding_service import EMBEDDING_DIM

    store_name = settings.vector_store.lower()

    if store_name == "pinecone":
        try:
            _store_instance = PineconeStore(
                api_key=settings.pinecone_api_key,
                index_name=settings.pinecone_index_name,
                dimension=EMBEDDING_DIM,
            )
            return _store_instance
        except (VectorStoreError, Exception) as e:
            logger.warning(f"Pinecone unavailable ({e}); falling back to local FAISS vector store.")

    _store_instance = FAISSStore(dimension=EMBEDDING_DIM)
    return _store_instance


def reset_vector_store_cache() -> None:
    """Used by tests to force re-initialization after changing settings."""
    global _store_instance
    _store_instance = None
