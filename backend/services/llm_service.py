"""
backend/services/llm_service.py

LLM provider abstraction. Every agent that needs an LLM call goes through
`get_llm_provider()` rather than importing a specific SDK directly, so we
can swap providers via config without touching agent code.

    LLMProvider (ABC)
    ├── GeminiProvider       - Google Gemini API
    ├── OpenAIProvider       - OpenAI-compatible API (also covers Groq via base_url)
    └── MockProvider         - deterministic canned responses, no network/API key needed

Two methods are exposed:
    - generate_text(prompt, system_prompt=None) -> str
    - generate_json(prompt, system_prompt=None) -> dict
      (prompts the model to return ONLY JSON, then parses it; raises
       LLMJSONParseError with the raw text attached if parsing fails, so
       callers can decide how to handle a malformed response rather than
       silently getting None)
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when an LLM call fails outright (network, auth, etc.)."""


class LLMJSONParseError(Exception):
    """Raised when generate_json can't parse the model's output as JSON."""

    def __init__(self, message: str, raw_text: str):
        super().__init__(message)
        self.raw_text = raw_text


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        ...

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict:
        """
        Default implementation: wrap the prompt with a strict JSON-only
        instruction, call generate_text, then parse. Providers can override
        if their SDK has native structured-output support.
        """
        json_system_prompt = (
            (system_prompt + "\n\n" if system_prompt else "")
            + "Respond with ONLY valid JSON. No preamble, no markdown code fences, "
            "no explanation before or after the JSON object."
        )
        raw = self.generate_text(prompt, system_prompt=json_system_prompt)
        cleaned = _strip_json_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise LLMJSONParseError(f"Failed to parse LLM output as JSON: {e}", raw_text=raw)


def _strip_json_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


class MockProvider(LLMProvider):
    """
    Deterministic, offline provider. Used when LLM_PROVIDER=mock, or as an
    explicit fallback for tests, so the rest of the system is testable
    without burning API calls or requiring a key.

    Never presented to the user as if it were a real model response —
    callers/trace should label output from this provider as "mock".
    """
    name = "mock"

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return f"[MOCK RESPONSE] This is a deterministic mock reply to a prompt of {len(prompt)} characters."

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict:
        # Return a plausible, clearly-mock structured object rather than
        # trying to parse free text, so JSON-consuming callers always work
        # offline too.
        return {
            "mock": True,
            "note": "This is a MockProvider response for offline development/testing.",
        }


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite"):
        if not api_key:
            raise LLMError("GEMINI_API_KEY is not set but LLM_PROVIDER=gemini")
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            from google.genai import types
            config = types.GenerateContentConfig(system_instruction=system_prompt) if system_prompt else None
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
            if not response or not getattr(response, "text", None):
                raise LLMError("Gemini returned an empty response")
            return response.text
        except LLMError:
            raise
        except Exception as e:
            logger.exception("Gemini generation failed")
            raise LLMError(f"Gemini API call failed: {e}") from e


class OpenAIProvider(LLMProvider):
    """
    Covers both real OpenAI and any OpenAI-compatible endpoint (e.g. Groq)
    by accepting a custom base_url.
    """
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        if not api_key:
            raise LLMError("API key is not set but LLM_PROVIDER=openai")
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key, base_url=base_url or None)
        self._model = model

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
            )
            content = response.choices[0].message.content
            if not content:
                raise LLMError("OpenAI-compatible API returned an empty response")
            return content
        except LLMError:
            raise
        except Exception as e:
            logger.exception("OpenAI-compatible generation failed")
            raise LLMError(f"OpenAI-compatible API call failed: {e}") from e


_provider_instance: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """
    Returns a cached provider instance based on settings.llm_provider.
    Falls back to MockProvider with a logged warning if the configured
    provider can't be constructed (e.g. missing API key), so the app
    degrades gracefully instead of crashing.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_name = settings.llm_provider.lower()

    try:
        if provider_name == "gemini":
            _provider_instance = GeminiProvider(api_key=settings.gemini_api_key)
        elif provider_name == "openai":
            _provider_instance = OpenAIProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or None,
            )
        elif provider_name == "groq":
            _provider_instance = OpenAIProvider(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                model="llama-3.1-8b-instant",
            )
        elif provider_name == "mock":
            _provider_instance = MockProvider()
        else:
            logger.warning(f"Unknown LLM_PROVIDER '{provider_name}', falling back to mock.")
            _provider_instance = MockProvider()
    except LLMError as e:
        logger.warning(f"Failed to initialize '{provider_name}' provider ({e}); falling back to mock.")
        _provider_instance = MockProvider()

    return _provider_instance


def reset_llm_provider_cache() -> None:
    """Used by tests to force re-initialization after changing settings."""
    global _provider_instance
    _provider_instance = None
