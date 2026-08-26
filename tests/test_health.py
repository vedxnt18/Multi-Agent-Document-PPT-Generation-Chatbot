"""
tests/test_health.py

Phase 1 tests: backend boots, /health responds, /upload validates correctly.
Run with:
    pytest -v
(from the project root, with the venv activated)
"""
import io
import sys
from pathlib import Path

# Ensure project root is on sys.path when running `pytest` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "llm_provider" in body


def test_upload_rejects_bad_extension():
    fake_file = io.BytesIO(b"not a real docx")
    resp = client.post(
        "/upload",
        files={"file": ("malware.exe", fake_file, "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_upload_accepts_valid_extension():
    fake_file = io.BytesIO(b"fake pdf bytes")
    resp = client.post(
        "/upload",
        files={"file": ("sample.pdf", fake_file, "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["file"]["extension"] == ".pdf"
    assert Path(body["file"]["stored_path"]).exists()
