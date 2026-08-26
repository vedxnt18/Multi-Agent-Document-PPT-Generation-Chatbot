"""
tests/test_template_analysis.py

Phase 3 tests. LLM classification runs against MockProvider by default in
this test environment (no real key configured), so we assert the
mock-labeled behavior for those fields, and fully verify all structural
(non-LLM) facts since those are deterministic.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.extraction_service import extract_file
from backend.agents.document_analyzer import analyze_document
from backend.agents.ppt_analyzer import analyze_ppt

client = TestClient(app)
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_analyze_document_structural_facts():
    extraction = extract_file(str(FIXTURES / "sample.docx"), "test-doc", "sample.docx")
    spec = analyze_document(extraction)

    assert spec.has_title is True
    assert "Executive Summary" in spec.section_titles
    assert "Market Overview" in spec.section_titles
    assert len(spec.tables) == 1
    assert spec.tables[0].row_count == 2
    assert spec.tables[0].col_count == 2
    assert spec.body_paragraph_count >= 2
    # LLM classification runs against MockProvider in this environment
    assert "mock" in spec.document_type.lower()
    assert "mock" in spec.tone.lower()


def test_analyze_document_empty_extraction_handled_gracefully():
    from backend.schemas.extraction import ExtractionResult
    empty = ExtractionResult(file_id="empty", original_filename="empty.docx", file_extension=".docx", document_type="docx")
    spec = analyze_document(empty)
    assert spec.warnings  # should warn, not crash
    assert spec.body_paragraph_count == 0


def test_analyze_ppt_structural_facts():
    extraction = extract_file(str(FIXTURES / "sample.pptx"), "test-ppt", "sample.pptx")
    spec = analyze_ppt(extraction, str(FIXTURES / "sample.pptx"))

    assert spec.slide_count == 1
    assert spec.slide_width_in is not None and spec.slide_width_in > 0
    assert len(spec.slide_patterns) == 1
    assert spec.slide_patterns[0].has_title is True
    assert spec.content_density in ("light", "moderate", "dense")
    assert "mock" in spec.visual_style.lower()


def test_analyze_api_docx_end_to_end():
    with open(FIXTURES / "sample.docx", "rb") as f:
        upload_resp = client.post(
            "/upload",
            files={"file": ("sample.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    file_id = upload_resp.json()["file"]["file_id"]

    analyze_resp = client.post(f"/analyze/{file_id}")
    assert analyze_resp.status_code == 200
    body = analyze_resp.json()
    assert "heading_hierarchy" in body
    assert len(body["heading_hierarchy"]) > 0


def test_analyze_api_pptx_end_to_end():
    with open(FIXTURES / "sample.pptx", "rb") as f:
        upload_resp = client.post(
            "/upload",
            files={"file": ("sample.pptx", f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
        )
    file_id = upload_resp.json()["file"]["file_id"]

    analyze_resp = client.post(f"/analyze/{file_id}")
    assert analyze_resp.status_code == 200
    body = analyze_resp.json()
    assert body["slide_count"] == 1


def test_analyze_api_rejects_image():
    with open(FIXTURES / "sample_text.png", "rb") as f:
        upload_resp = client.post("/upload", files={"file": ("sample_text.png", f, "image/png")})
    file_id = upload_resp.json()["file"]["file_id"]

    analyze_resp = client.post(f"/analyze/{file_id}")
    assert analyze_resp.status_code == 422
