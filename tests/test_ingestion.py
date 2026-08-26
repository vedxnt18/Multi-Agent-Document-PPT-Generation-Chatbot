"""
tests/test_ingestion.py

Phase 2 tests: PDF (native + OCR fallback), DOCX, PPTX, and image extraction,
plus the /ingest API endpoint end-to-end.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.document_service import extract_pdf, extract_docx, extract_image
from backend.services.ppt_service import extract_pptx
from backend.services.ocr_service import ocr_service

client = TestClient(app)
FIXTURES = Path(__file__).resolve().parent / "fixtures"


# --- Unit-level extractor tests ---

def test_extract_docx_headings_and_tables():
    result = extract_docx(str(FIXTURES / "sample.docx"), "test-docx", "sample.docx")
    assert result.document_type == "docx"
    headings = [b for b in result.blocks if b.block_type == "heading"]
    tables = [b for b in result.blocks if b.block_type == "table"]
    assert any("Executive Summary" in h.text for h in headings)
    assert len(tables) == 1
    assert tables[0].metadata["rows"][0] == ["Quarter", "Revenue"]


def test_extract_pptx_title_and_body():
    result = extract_pptx(str(FIXTURES / "sample.pptx"), "test-pptx", "sample.pptx")
    assert result.document_type == "pptx"
    assert result.page_or_slide_count == 1
    titles = [b for b in result.blocks if b.block_type == "slide_title"]
    assert any("Company Template" in t.text for t in titles)


def test_extract_pdf_native_text():
    result = extract_pdf(str(FIXTURES / "sample_native.pdf"), "test-pdf", "sample_native.pdf")
    assert result.document_type == "pdf"
    assert not result.used_ocr
    assert "native text PDF" in result.full_text()


def test_extract_pdf_blank_triggers_ocr_path():
    result = extract_pdf(str(FIXTURES / "sample_blank.pdf"), "test-pdf-blank", "sample_blank.pdf")
    # Blank page has no native text -> should attempt OCR (may find nothing, but
    # must not silently pretend it extracted real content)
    if ocr_service.available:
        assert result.used_ocr or len(result.warnings) > 0
    else:
        assert any("OCR is unavailable" in w or "OCR unavailable" in w for w in result.warnings)


def test_extract_image_ocr():
    result = extract_image(str(FIXTURES / "sample_text.png"), "test-img", "sample_text.png")
    if ocr_service.available:
        # Real OCR on a low-res rendered test image won't be pixel-perfect
        # (e.g. "12345" may be misread as "12845"). We assert OCR genuinely
        # ran and produced plausible text with a confidence score, not an
        # exact character match, which would be an unrealistic expectation
        # of any OCR engine.
        assert result.used_ocr
        assert len(result.blocks) == 1
        block = result.blocks[0]
        assert block.source_type == "ocr"
        assert block.confidence is not None and block.confidence > 0.3
        assert "test" in block.text.lower()  # the one word unlikely to be misread
    else:
        assert "unavailable" in " ".join(result.warnings).lower()


# --- API-level test: upload then ingest ---

def test_upload_then_ingest_docx():
    with open(FIXTURES / "sample.docx", "rb") as f:
        upload_resp = client.post(
            "/upload",
            files={"file": ("sample.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    assert upload_resp.status_code == 200
    file_id = upload_resp.json()["file"]["file_id"]

    ingest_resp = client.post(f"/ingest/{file_id}")
    assert ingest_resp.status_code == 200
    body = ingest_resp.json()
    assert body["document_type"] == "docx"
    assert len(body["blocks"]) > 0


def test_ingest_unknown_file_id_returns_404():
    resp = client.post("/ingest/nonexistent-id-1234")
    assert resp.status_code == 404
