"""
tests/test_llm_service.py

Phase 4 tests. Since no live API keys are configured in this environment,
these tests focus on what's fully testable offline:
  - MockProvider behavior
  - JSON fence-stripping / parsing logic (shared by all providers via the
    base class's generate_json)
  - graceful fallback to MockProvider when a configured provider can't be
    constructed (e.g. missing key)

Live Gemini/OpenAI calls are exercised manually once a real key is present
in .env (see README "Testing the LLM abstraction with a real key").
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.llm_service import (
    MockProvider,
    LLMProvider,
    LLMJSONParseError,
    get_llm_provider,
    reset_llm_provider_cache,
    _strip_json_fences,
)
from backend.config import settings


def test_mock_provider_generate_text():
    provider = MockProvider()
    result = provider.generate_text("hello world")
    assert "MOCK RESPONSE" in result
    assert isinstance(result, str)


def test_mock_provider_generate_json():
    provider = MockProvider()
    result = provider.generate_json("give me json")
    assert isinstance(result, dict)
    assert result["mock"] is True


def test_strip_json_fences_removes_markdown():
    raw = '```json\n{"a": 1}\n```'
    assert _strip_json_fences(raw) == '{"a": 1}'


def test_strip_json_fences_passthrough_plain_json():
    raw = '{"a": 1}'
    assert _strip_json_fences(raw) == '{"a": 1}'


class _FakeTextOnlyProvider(LLMProvider):
    """A minimal provider used to test the base class's generate_json fallback logic."""
    name = "fake"

    def __init__(self, canned_response: str):
        self._canned = canned_response

    def generate_text(self, prompt, system_prompt=None):
        return self._canned


def test_base_generate_json_parses_fenced_output():
    provider = _FakeTextOnlyProvider('```json\n{"tone": "professional"}\n```')
    result = provider.generate_json("classify tone")
    assert result == {"tone": "professional"}


def test_base_generate_json_raises_on_invalid_json():
    provider = _FakeTextOnlyProvider("this is not json at all")
    try:
        provider.generate_json("classify tone")
        assert False, "expected LLMJSONParseError"
    except LLMJSONParseError as e:
        assert "not json" in e.raw_text


def test_get_llm_provider_falls_back_to_mock_when_gemini_key_missing():
    reset_llm_provider_cache()
    original_provider = settings.llm_provider
    original_key = settings.gemini_api_key
    try:
        settings.llm_provider = "gemini"
        settings.gemini_api_key = ""  # force failure
        provider = get_llm_provider()
        assert provider.name == "mock"
    finally:
        settings.llm_provider = original_provider
        settings.gemini_api_key = original_key
        reset_llm_provider_cache()


def test_get_llm_provider_returns_mock_when_configured():
    reset_llm_provider_cache()
    original_provider = settings.llm_provider
    try:
        settings.llm_provider = "mock"
        provider = get_llm_provider()
        assert provider.name == "mock"
    finally:
        settings.llm_provider = original_provider
        reset_llm_provider_cache()
