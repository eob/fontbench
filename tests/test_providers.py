"""Provider request contracts, metering, and billing-stop classification, offline."""

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import httpx
import pytest
from PIL import Image

from baseline import evaluator


PREDICTION = {
    "font": "Arial", "category": "non-serif", "weight": "regular",
    "modifier": "regular", "kerning": "normal", "line_height": "normal",
}


@pytest.fixture
def image_path(tmp_path):
    path = tmp_path / "sample.png"
    Image.new("RGB", (4, 4), "white").save(path)
    return path


def provider_client(monkeypatch, provider, handler, **kwargs):
    from baseline import providers
    original_client = httpx.Client
    monkeypatch.setenv("TEST_PROVIDER_KEY", "test-secret-key")
    monkeypatch.setattr(providers.httpx, "Client", lambda **options: original_client(transport=httpx.MockTransport(handler), **options))
    monkeypatch.setattr(providers.time, "sleep", lambda _: None)
    return providers.PredictionClient(provider, "test-model", api_key_env="TEST_PROVIDER_KEY", **kwargs)


def success_body(provider, raw=None, input_tokens=12, output_tokens=5):
    raw = json.dumps(PREDICTION) if raw is None else raw
    if provider == "openai":
        return {"status": "completed", "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [{"type": "output_text", "text": raw}]},
        ], "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens}}
    if provider == "anthropic":
        return {"stop_reason": "end_turn", "content": [{"type": "thinking", "thinking": "hidden"}, {"type": "text", "text": raw}],
                "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens}}
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"thought": True, "text": "hidden"}, {"text": raw}]}}],
            "usageMetadata": {"promptTokenCount": input_tokens, "candidatesTokenCount": output_tokens, "thoughtsTokenCount": 3}}


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_provider_sends_native_image_and_schema_and_preserves_metering(monkeypatch, image_path, provider):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=success_body(provider))
    client = provider_client(monkeypatch, provider, handler, max_output_tokens=321)
    result = client.predict(str(image_path), "Describe typography")
    client.close()
    assert result.parsed == PREDICTION
    assert result.raw_text == json.dumps(PREDICTION)
    assert result.error is None
    assert result.input_tokens == 12
    assert result.output_tokens == (8 if provider == "google" else 5)
    assert result.request_attempts == 1
    assert result.unmetered_attempts == 0
    body = json.loads(requests[0].content)
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    if provider == "openai":
        assert requests[0].url == "https://api.openai.com/v1/responses"
        assert requests[0].headers["authorization"] == "Bearer test-secret-key"
        assert body["input"][0]["content"][0]["image_url"] == f"data:image/png;base64,{encoded}"
        assert body["text"]["format"]["strict"] is True
        schema = body["text"]["format"]["schema"]
        assert body["max_output_tokens"] == 321
        assert body["store"] is False
    elif provider == "anthropic":
        assert requests[0].url == "https://api.anthropic.com/v1/messages"
        assert requests[0].headers["x-api-key"] == "test-secret-key"
        assert requests[0].headers["anthropic-version"] == "2023-06-01"
        assert body["messages"][0]["content"][0]["source"]["data"] == encoded
        schema = body["output_config"]["format"]["schema"]
        assert "minLength" not in schema["properties"]["font"]
        assert body["max_tokens"] == 321
    else:
        assert requests[0].url == "https://generativelanguage.googleapis.com/v1beta/models/test-model:generateContent"
        assert requests[0].headers["x-goog-api-key"] == "test-secret-key"
        assert body["contents"][0]["parts"][0]["inlineData"]["data"] == encoded
        schema = body["generationConfig"]["responseJsonSchema"]
        assert body["generationConfig"]["maxOutputTokens"] == 321
    assert set(schema["required"]) == set(PREDICTION)
    assert schema["additionalProperties"] is False
    assert "temperature" not in body


@pytest.mark.parametrize("provider,status,error,kind", [
    ("openai", 429, {"code": "insufficient_quota", "message": "Quota exceeded"}, "credits"),
    ("openai", 429, {"code": "credit_balance_exhausted", "message": "No credits"}, "credits"),
    ("openai", 429, {"code": "project_spend_limit_exceeded", "message": "Spend limit reached"}, "credits"),
    ("anthropic", 400, {"type": "invalid_request_error", "message": "Your credit balance is too low to access the Anthropic API."}, "credits"),
    ("anthropic", 402, {"type": "billing_error", "message": "Payment required"}, "credits"),
    ("anthropic", 429, {"type": "rate_limit_error", "message": "Your account has reached its monthly spend limit."}, "credits"),
    ("google", 400, {"status": "FAILED_PRECONDITION", "message": "Billing is not enabled for this project"}, "credits"),
    ("openai", 401, {"code": "invalid_api_key", "message": "Invalid API key test-secret-key"}, "authentication"),
    ("google", 403, {"status": "PERMISSION_DENIED", "message": "Permission denied"}, "authentication"),
    ("anthropic", 404, {"type": "not_found_error", "message": "Model unavailable"}, "unavailable"),
])
def test_terminal_errors_are_classified_without_retry_or_key_leak(monkeypatch, image_path, provider, status, error, kind):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": error})
    client = provider_client(monkeypatch, provider, handler)
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.error_kind == kind
    assert result.parsed == {}
    assert result.request_attempts == 1
    assert len(calls) == 1
    assert "test-secret-key" not in result.error
    assert "test-secret-key" not in result.raw_text


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_rate_limits_retry_at_most_once_and_remain_distinct_from_credit_errors(monkeypatch, image_path, provider):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, json={"error": {"message": "Per-minute request rate exceeded", "type": "rate_limit_error", "status": "RESOURCE_EXHAUSTED"}}, headers={"retry-after": "0"})
    client = provider_client(monkeypatch, provider, handler)
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.error_kind == "rate_limit"
    assert result.request_attempts == len(calls) == 2


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_invalid_billable_responses_are_not_retried_and_keep_usage(monkeypatch, image_path, provider):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=success_body(provider, raw="{}"))
    client = provider_client(monkeypatch, provider, handler)
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.error_kind == "invalid_response"
    assert result.raw_text == "{}"
    assert result.parsed == {}
    assert result.input_tokens == 12
    assert result.output_tokens == (8 if provider == "google" else 5)
    assert len(calls) == 1


def test_transport_retry_keeps_unknown_charge_exposure_separate_from_metered_usage(monkeypatch, image_path):
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json=success_body("openai"))
    client = provider_client(monkeypatch, "openai", handler)
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.error is None
    assert result.input_tokens == 12
    assert result.output_tokens == 5
    assert result.request_attempts == 2
    assert result.unmetered_attempts == 1


def test_missing_key_is_a_local_authentication_failure(monkeypatch, image_path):
    from baseline.providers import PredictionClient
    monkeypatch.delenv("ABSENT_TEST_KEY", raising=False)
    client = PredictionClient("openai", "model", api_key_env="ABSENT_TEST_KEY")
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.error_kind == "authentication"
    assert result.request_attempts == 0
    assert result.unmetered_attempts == 0


def test_evaluator_propagates_per_task_usage_without_shared_state(monkeypatch, image_path):
    from baseline.providers import PredictionResponse
    instance = evaluator.BaselineEvaluator(model_name="example", provider="openai", mock=True)
    def predict(path, prompt):
        tokens = int(prompt)
        return PredictionResponse(json.dumps(PREDICTION), PREDICTION, input_tokens=tokens, output_tokens=2)
    instance.predict_image = predict
    def task(index):
        return {"taskId": str(index), "fontId": "arial", "fontName": "Arial", "aliases": [],
                "category": "non-serif", "weight": "regular", "modifier": "regular", "kerning": "normal",
                "lineHeight": "normal", "widthId": "narrow", "widthPx": 220, "imagePath": str(image_path), "prompt": str(index)}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda i: instance._eval_single_task(task(i), "prompt"), range(1, 9)))
    assert [r.input_tokens for r in results] == list(range(1, 9))
    assert all(r.provider == "openai" and r.all_correct for r in results)
    scorecard = instance.score_results(results, expected_task_count=10)
    assert scorecard.total_tasks == 8
    assert scorecard.expected_task_count == 10
    assert scorecard.provider == "openai"
    assert scorecard.overall_exact_match == 1.0


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_truncated_responses_keep_usage_but_are_not_graded(monkeypatch, image_path, provider):
    body = success_body(provider)
    if provider == "openai":
        body["status"] = "incomplete"
    elif provider == "anthropic":
        body["stop_reason"] = "max_tokens"
    else:
        body["candidates"][0]["finishReason"] = "MAX_TOKENS"
    client = provider_client(monkeypatch, provider, lambda request: httpx.Response(200, json=body))
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.error_kind == "invalid_response"
    assert result.parsed == {}
    assert result.input_tokens == 12
    assert result.request_attempts == 1


@pytest.mark.parametrize("provider,field", [("google", "thoughtsTokenCount"), ("anthropic", "cache_read_input_tokens")])
def test_malformed_usage_metadata_is_unmetered_instead_of_crashing(monkeypatch, image_path, provider, field):
    body = success_body(provider)
    body["usageMetadata" if provider == "google" else "usage"][field] = "not a token count"
    client = provider_client(monkeypatch, provider, lambda request: httpx.Response(200, json=body))
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.parsed == PREDICTION
    assert result.unmetered_attempts == 1


def test_anthropic_cached_input_is_not_omitted_from_usage(monkeypatch, image_path):
    body = success_body("anthropic")
    body["usage"].update(cache_read_input_tokens=20, cache_creation_input_tokens=10)
    client = provider_client(monkeypatch, "anthropic", lambda request: httpx.Response(200, json=body))
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.input_tokens == 42


def test_short_retry_after_is_honored_and_long_backoff_returns_control(monkeypatch, image_path):
    from baseline import providers
    handler = Mock(return_value=httpx.Response(429, json={"error": {"message": "Rate limit"}}, headers={"retry-after": "120"}))
    client = provider_client(monkeypatch, "openai", handler)
    sleeps = Mock()
    monkeypatch.setattr(providers.time, "sleep", sleeps)
    result = client.predict(str(image_path), "prompt")
    assert result.error_kind == "rate_limit"
    assert result.request_attempts == 1
    sleeps.assert_not_called()
    handler.return_value = httpx.Response(429, json={"error": {"message": "Rate limit"}}, headers={"retry-after": "2"})
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.request_attempts == 2
    sleeps.assert_called_once_with(2.0)


def test_failed_response_cannot_receive_credit_even_if_parsed_data_is_present(monkeypatch, image_path):
    from baseline.providers import PredictionResponse
    instance = evaluator.BaselineEvaluator(mock=True)
    instance.predict_image = Mock(return_value=PredictionResponse("raw", PREDICTION, error="Out of credits", error_kind="credits"))
    task = {"taskId": "a", "fontId": "arial", "fontName": "Arial", "aliases": [], "category": "non-serif",
            "weight": "regular", "modifier": "regular", "kerning": "normal", "lineHeight": "normal",
            "widthId": "narrow", "widthPx": 220, "imagePath": str(image_path)}
    result = instance._eval_single_task(task, "prompt")
    assert result.composite_score == 0
    assert result.error_kind == "credits"


def test_refusal_body_is_preserved_for_auditing(monkeypatch, image_path):
    body = {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "Cannot answer this request"}]}],
            "usage": {"input_tokens": 7, "output_tokens": 3}}
    client = provider_client(monkeypatch, "openai", lambda request: httpx.Response(200, json=body))
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.error_kind == "invalid_response"
    assert "Cannot answer this request" in result.raw_text
    assert result.output_tokens == 3


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_invalid_request_configuration_is_unavailable_without_retry(monkeypatch, image_path, provider):
    handler = Mock(return_value=httpx.Response(400, json={"error": {"status": "INVALID_ARGUMENT", "type": "invalid_request_error", "message": "Structured output is not supported by this model"}}))
    client = provider_client(monkeypatch, provider, handler)
    result = client.predict(str(image_path), "prompt")
    client.close()
    assert result.error_kind == "unavailable"
    assert result.request_attempts == handler.call_count == 1


@pytest.mark.parametrize('provider', ['openai', 'anthropic', 'google'])
@pytest.mark.parametrize('raw', [
    json.dumps({**PREDICTION, 'font': '   '}),
    json.dumps({**PREDICTION, 'alternative_font': 'Helvetica'}),
    '{"font":"Helvetica",' + json.dumps(PREDICTION)[1:],
])
def test_ambiguous_answers_are_final_schema_errors(monkeypatch, image_path, provider, raw):
    handler = Mock(return_value=httpx.Response(200, json=success_body(provider, raw=raw)))
    client = provider_client(monkeypatch, provider, handler)
    result = client.predict(str(image_path), 'prompt')
    client.close()
    assert result.error_kind == 'invalid_response'
    assert result.parsed == {}
    assert result.request_attempts == handler.call_count == 1


def test_valid_prediction_whitespace_is_normalized_consistently(monkeypatch, image_path):
    raw = json.dumps({key: f' {value.upper()} ' for key, value in PREDICTION.items()})
    client = provider_client(monkeypatch, 'openai', lambda request: httpx.Response(200, json=success_body('openai', raw=raw)))
    result = client.predict(str(image_path), 'prompt')
    client.close()
    assert result.parsed == {**PREDICTION, 'font': 'ARIAL'}
