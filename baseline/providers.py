"""Native vision requests, structured predictions, and per-request usage accounting."""

from __future__ import annotations

import base64
import io
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import quote

import httpx
from PIL import Image
from pydantic import BaseModel, Field


ErrorKind = Literal["credits", "rate_limit", "authentication", "unavailable", "invalid_response", "other"]


class TypographicPrediction(BaseModel):
    font: str = Field(min_length=1, description="The non-empty canonical font family name")
    category: Literal["serif", "non-serif", "mono", "handwriting", "other"]
    weight: Literal["thin", "regular", "bold", "black"]
    modifier: Literal["regular", "italic", "underline", "strikethrough", "small-caps"]
    kerning: Literal["tight", "normal", "loose"]
    line_height: Literal["tight", "normal", "loose"]


@dataclass
class PredictionResponse:
    raw_text: str
    parsed: dict = field(default_factory=dict)
    error: str | None = None
    error_kind: ErrorKind | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    request_attempts: int = 0
    unmetered_attempts: int = 0


PROVIDERS = {
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "anthropic": ("https://api.anthropic.com/v1", "ANTHROPIC_API_KEY"),
    "google": ("https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY"),
}


def classify_error(status: int, error: dict) -> ErrorKind:
    code = str(error.get("code", "")).lower()
    kind = str(error.get("type", "")).lower()
    message = str(error.get("message", "")).lower()
    if (status == 402 or kind in {"insufficient_quota", "billing_error"}
            or code in {"insufficient_quota", "credit_balance_exhausted", "billing_hard_limit_reached",
                        "organization_spend_limit_exceeded", "project_spend_limit_exceeded",
                        "organization_usage_limit_exceeded"}
            or any(term in message for term in (
                "credit balance", "insufficient credit", "out of credits", "spend limit",
                "spending limit", "spend cap", "billing is not enabled", "billing account is disabled",
                "billing account has been disabled", "billing_not_enabled",
            ))):
        return "credits"
    if status in {401, 403} or kind == "authentication_error" or code in {"invalid_api_key", "api_key_invalid"}:
        return "authentication"
    if "api key not valid" in message:
        return "authentication"
    if status == 429:
        return "rate_limit"
    if status in {400, 404, 408} or status >= 500:
        return "unavailable"
    return "other"


class PredictionClient:
    def __init__(
        self, provider: str, model: str, api_key_env: str | None = None,
        base_url: str | None = None, max_output_tokens: int = 1024,
    ):
        if provider not in PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        if not isinstance(max_output_tokens, int) or isinstance(max_output_tokens, bool) or max_output_tokens < 1:
            raise ValueError("max_output_tokens must be a positive integer")
        self.provider = provider
        self.model = model
        self.base_url = (base_url or PROVIDERS[provider][0]).rstrip("/")
        self.api_key_env = api_key_env or PROVIDERS[provider][1]
        self._google_key_fallback = provider == "google" and api_key_env is None
        self.max_output_tokens = max_output_tokens
        self._http = httpx.Client(timeout=60.0, follow_redirects=False)

    def close(self) -> None:
        self._http.close()

    def _request(self, data: str, mime_type: str, prompt: str, api_key: str) -> tuple[str, dict, dict]:
        schema = TypographicPrediction.model_json_schema()
        schema["additionalProperties"] = False
        headers = {"Content-Type": "application/json"}
        if self.provider == "openai":
            headers["Authorization"] = f"Bearer {api_key}"
            body = {
                "model": self.model, "store": False, "max_output_tokens": self.max_output_tokens,
                "input": [{"role": "user", "content": [
                    {"type": "input_image", "image_url": f"data:{mime_type};base64,{data}", "detail": "high"},
                    {"type": "input_text", "text": prompt},
                ]}],
                "text": {"format": {"type": "json_schema", "name": "fontbench_prediction", "schema": schema, "strict": True}},
            }
            return f"{self.base_url}/responses", headers, body
        if self.provider == "anthropic":
            headers.update({"x-api-key": api_key, "anthropic-version": "2023-06-01"})
            # Claude's grammar supports enum/object constraints but not minLength.
            schema["properties"]["font"].pop("minLength", None)
            body = {
                "model": self.model, "max_tokens": self.max_output_tokens,
                "messages": [{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": data}},
                    {"type": "text", "text": prompt},
                ]}],
                "output_config": {"format": {"type": "json_schema", "schema": schema}},
            }
            return f"{self.base_url}/messages", headers, body
        headers["x-goog-api-key"] = api_key
        model = quote(self.model.removeprefix("models/"), safe="")
        body = {
            "contents": [{"role": "user", "parts": [
                {"inlineData": {"mimeType": mime_type, "data": data}}, {"text": prompt},
            ]}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": schema,
                                 "maxOutputTokens": self.max_output_tokens},
        }
        return f"{self.base_url}/models/{model}:generateContent", headers, body

    def _usage(self, body: dict) -> tuple[int | None, int | None]:
        usage = body.get("usageMetadata" if self.provider == "google" else "usage") or {}
        if not isinstance(usage, dict):
            return None, None

        def total(required: str, *optional: str) -> int | None:
            counts = [usage.get(required)] + [usage.get(key, 0) for key in optional]
            if all(isinstance(count, int) and not isinstance(count, bool) and count >= 0 for count in counts):
                return sum(counts)
            return None

        if self.provider == "google":
            return total("promptTokenCount"), total("candidatesTokenCount", "thoughtsTokenCount")
        if self.provider == "anthropic":
            return total("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"), total("output_tokens")
        return total("input_tokens"), total("output_tokens")

    def _text(self, body: dict) -> str:
        if self.provider == "openai":
            if body.get("status") not in {None, "completed"}:
                raise ValueError(f"Response did not complete: {body.get('status')}")
            text = "".join(part["text"] for item in body.get("output", []) if item.get("type") == "message"
                           for part in item.get("content", []) if part.get("type") == "output_text")
        elif self.provider == "anthropic":
            if body.get("stop_reason") not in {None, "end_turn"}:
                raise ValueError(f"Response did not complete: {body.get('stop_reason')}")
            text = "".join(part["text"] for part in body.get("content", []) if part.get("type") == "text")
        else:
            candidates = body.get("candidates", [])
            if not candidates:
                raise ValueError("Response contained no candidates")
            candidate = candidates[0]
            if candidate.get("finishReason") not in {None, "STOP"}:
                raise ValueError(f"Response did not complete: {candidate.get('finishReason')}")
            text = "".join(part["text"] for part in candidate.get("content", {}).get("parts", [])
                          if "text" in part and not part.get("thought"))
        if not text:
            raise ValueError("Response contained no prediction text")
        return text

    def predict(self, image_path: str, prompt: str) -> PredictionResponse:
        api_key = os.environ.get(self.api_key_env)
        if not api_key and self._google_key_fallback:
            api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return PredictionResponse("", error=f"Missing API key environment variable: {self.api_key_env}", error_kind="authentication")
        try:
            raw_image = Path(image_path).read_bytes()
            with Image.open(io.BytesIO(raw_image)) as image:
                mime_type = Image.MIME.get(image.format, "image/png")
                image.verify()
        except (OSError, ValueError) as error:
            return PredictionResponse("", error=str(error), error_kind="other")
        url, headers, request_body = self._request(base64.b64encode(raw_image).decode("ascii"), mime_type, prompt, api_key)
        result = PredictionResponse("")
        for attempt in range(2):
            result.request_attempts += 1
            result.unmetered_attempts += 1
            retry_delay = 1.0
            try:
                response = self._http.post(url, headers=headers, json=request_body)
            except httpx.RequestError as error:
                result.error = str(error).replace(api_key, "[REDACTED]")
                result.error_kind = "unavailable"
                retryable = True
            else:
                result.raw_text = response.text.replace(api_key, "[REDACTED]")
                try:
                    body = response.json()
                    if not isinstance(body, dict):
                        raise ValueError("Provider response must be a JSON object")
                except ValueError as error:
                    body = {}
                    result.error = str(error)
                    result.error_kind = "invalid_response"
                input_tokens, output_tokens = self._usage(body)
                if input_tokens is not None:
                    result.input_tokens = (result.input_tokens or 0) + input_tokens
                if output_tokens is not None:
                    result.output_tokens = (result.output_tokens or 0) + output_tokens
                if input_tokens is not None and output_tokens is not None:
                    result.unmetered_attempts -= 1
                if response.is_success and not body.get("error"):
                    try:
                        result.raw_text = self._text(body).replace(api_key, "[REDACTED]")
                        parsed = json.loads(result.raw_text)
                        # Some structured-output providers preserve labels with different casing.
                        if isinstance(parsed, dict):
                            parsed = {key: value.strip().lower() if key != "font" and isinstance(value, str) else value
                                      for key, value in parsed.items()}
                        result.parsed = TypographicPrediction.model_validate(parsed).model_dump()
                        result.error = result.error_kind = None
                    except (ValueError, TypeError, KeyError, AttributeError) as error:
                        result.error = str(error).replace(api_key, "[REDACTED]")
                        result.error_kind = "invalid_response"
                    return result
                error = body.get("error") or {"message": result.raw_text}
                if not isinstance(error, dict):
                    error = {"message": str(error)}
                result.error_kind = classify_error(response.status_code, error)
                result.error = f"HTTP {response.status_code}: {error.get('message', result.raw_text)}".replace(api_key, "[REDACTED]")
                retryable = (response.status_code in {408, 429} or response.status_code >= 500) and result.error_kind not in {"credits", "authentication"}
                try:
                    retry_delay = max(0.0, float(response.headers.get("retry-after", "1")))
                except ValueError:
                    pass
            if not retryable or attempt == 1 or retry_delay > 60:
                return result
            time.sleep(retry_delay)
        return result
