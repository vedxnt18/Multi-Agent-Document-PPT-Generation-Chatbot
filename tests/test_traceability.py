"""
tests/test_traceability.py

Phase 14 tests: verifies /chat orchestration produces a persisted, queryable
trace record via GET /trace/{trace_id}.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.citation_service import citation_registry
from backend.services import trace_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    citation_registry.reset()
    yield


def test_chat_produces_trace_id():
    resp = client.post("/chat", json={"message": "Research AI trends", "file_ids": []})
    assert resp.status_code == 200
    body = resp.json()
    assert body["trace_id"] is not None
    assert body["trace_id"].startswith("trace_")


def test_trace_retrievable_via_api():
    chat_resp = client.post("/chat", json={"message": "Research AI trends", "file_ids": []})
    trace_id = chat_resp.json()["trace_id"]

    trace_resp = client.get(f"/trace/{trace_id}")
    assert trace_resp.status_code == 200
    body = trace_resp.json()
    assert body["user_request"] == "Research AI trends"
    assert "agent_calls" in body
    assert "plan" in body


def test_trace_nonexistent_404():
    resp = client.get("/trace/does-not-exist")
    assert resp.status_code == 404


def test_list_recent_traces():
    client.post("/chat", json={"message": "test trace listing", "file_ids": []})
    resp = client.get("/trace")
    assert resp.status_code == 200
    traces = resp.json()
    assert len(traces) >= 1
    assert "trace_id" in traces[0]
