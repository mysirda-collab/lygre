import json
import logging
from typing import Any, Protocol
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

log = logging.getLogger(__name__)


class StructuredExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: dict[str, str | None]
    confidence: dict[str, float] = Field(default_factory=dict)


class AiExtractionProvider(Protocol):
    def extract(self, text: str, parser_values: dict[str, Any]) -> StructuredExtraction: ...


class HttpAiExtractionProvider:
    """Provider-neutral JSON endpoint configured entirely through environment variables."""

    def extract(self, text: str, parser_values: dict[str, Any]) -> StructuredExtraction:
        if not settings.ai_extraction_endpoint:
            raise RuntimeError("AI extraction endpoint is not configured")
        headers = {"Content-Type": "application/json"}
        if settings.ai_extraction_api_key:
            headers["Authorization"] = f"Bearer {settings.ai_extraction_api_key}"
        request = Request(
            settings.ai_extraction_endpoint,
            data=json.dumps({"text": text, "parser_values": parser_values}).encode(),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=settings.ai_extraction_timeout_seconds) as response:
            return StructuredExtraction.model_validate_json(response.read())


def enrich_with_optional_ai(text: str, parser_values: dict[str, Any]) -> dict[str, Any]:
    result = dict(parser_values)
    result.setdefault("field_sources", {key: "parser" for key, value in result.items() if value})
    if not settings.ai_extraction_enabled:
        return result
    try:
        extraction = HttpAiExtractionProvider().extract(text, parser_values)
    except Exception:
        log.exception("Volitelná AI extrakce selhala; pokračuji s výsledkem parseru")
        result["ai_extraction_error"] = True
        return result
    sources = dict(result["field_sources"])
    for key, value in extraction.values.items():
        if value and not result.get(key):
            result[key] = value
            sources[key] = "ai"
    result["field_sources"] = sources
    result["ai_confidence"] = extraction.confidence
    return result
