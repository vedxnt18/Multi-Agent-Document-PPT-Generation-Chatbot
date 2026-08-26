"""
backend/services/citation_service.py

Source registry for end-to-end traceability. Every piece of content that
enters the system from an uploaded document, RAG retrieval, or web search
gets a citation ID (e.g. DOC-001, RAG-001, WEB-001), so generated content
can always be traced back to where it came from.

This is an in-memory registry per process for now; Phase 13/14 (versioning
+ traceability) will persist it to SQLite alongside artifacts.
"""
from dataclasses import dataclass, field
from typing import Optional
from itertools import count


@dataclass
class Source:
    citation_id: str
    source_type: str          # "DOC" | "RAG" | "WEB"
    title: str
    detail: str                # filename, URL, or chunk description
    metadata: dict = field(default_factory=dict)


class CitationRegistry:
    def __init__(self):
        self._sources: dict[str, Source] = {}
        self._counters = {"DOC": count(1), "RAG": count(1), "WEB": count(1)}

    def register(self, source_type: str, title: str, detail: str, metadata: Optional[dict] = None) -> str:
        if source_type not in self._counters:
            raise ValueError(f"Unknown source_type '{source_type}', expected DOC/RAG/WEB")
        n = next(self._counters[source_type])
        citation_id = f"{source_type}-{n:03d}"
        self._sources[citation_id] = Source(
            citation_id=citation_id,
            source_type=source_type,
            title=title,
            detail=detail,
            metadata=metadata or {},
        )
        return citation_id

    def get(self, citation_id: str) -> Optional[Source]:
        return self._sources.get(citation_id)

    def all(self) -> dict[str, Source]:
        return dict(self._sources)

    def reset(self) -> None:
        self._sources.clear()
        self._counters = {"DOC": count(1), "RAG": count(1), "WEB": count(1)}


# Process-wide registry. In later phases this becomes per-conversation/
# per-request state persisted to SQLite rather than a single global.
citation_registry = CitationRegistry()
