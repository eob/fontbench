"""Model catalogs remain explicit, bounded, and safe for result filenames."""

import json
from collections import Counter
from pathlib import Path

import pytest

from baseline.model_config import load_model_config


MODEL = {
    "id": "openai-test", "provider": "openai", "model": "exact-api-model",
    "display_name": "Test model", "api_key_env": "OPENAI_API_KEY",
    "source_url": "https://developers.openai.com/api/docs/models",
    "input_per_m": 1.0, "output_per_m": 5.0, "max_output_tokens": 1024,
    "enabled": True,
}


def catalog(tmp_path, models, **overrides):
    path = tmp_path / "models.json"
    path.write_text(json.dumps({"version": 1, "verified_at": "2026-09-07", "models": models, **overrides}))
    return path


def test_load_keeps_exact_api_ids_and_filters_disabled_models(tmp_path):
    records = load_model_config(catalog(tmp_path, [MODEL, {**MODEL, "id": "disabled", "enabled": False}]))
    assert len(records) == 1
    assert records[0]["model"] == "exact-api-model"
    assert records[0]["max_output_tokens"] == 1024


@pytest.mark.parametrize("field,value", [
    ("id", "../escape"), ("id", "/absolute"), ("model", ""),
    ("provider", "unknown"), ("api_key_env", "literal-secret-value"),
    ("max_output_tokens", 0), ("max_output_tokens", -1), ("max_output_tokens", True),
    ("input_per_m", -1), ("input_per_m", float("nan")),
    ("output_per_m", float("inf")), ("input_per_m", True),
    ("enabled", "false"), ("source_url", "javascript:alert(1)"),
])
def test_invalid_model_configuration_is_rejected(tmp_path, field, value):
    with pytest.raises(ValueError):
        load_model_config(catalog(tmp_path, [{**MODEL, field: value}]))


def test_duplicate_ids_are_rejected_even_when_disabled(tmp_path):
    with pytest.raises(ValueError, match="Duplicate"):
        load_model_config(catalog(tmp_path, [MODEL, {**MODEL, "enabled": False}]))


def test_more_than_five_enabled_models_per_vendor_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="five"):
        load_model_config(catalog(tmp_path, [{**MODEL, "id": f"model-{i}"} for i in range(6)]))


def test_disabled_models_do_not_count_toward_vendor_limit(tmp_path):
    records = [{**MODEL, "id": f"model-{i}", "enabled": i < 5} for i in range(6)]
    assert len(load_model_config(catalog(tmp_path, records))) == 5


def test_unknown_prices_remain_unknown(tmp_path):
    model = {**MODEL, "input_per_m": None, "output_per_m": None}
    assert load_model_config(catalog(tmp_path, [model]))[0]["input_per_m"] is None


@pytest.mark.parametrize("overrides", [{"version": 2}, {"version": True}, {"verified_at": "yesterday"}])
def test_invalid_catalog_metadata_is_rejected(tmp_path, overrides):
    with pytest.raises(ValueError):
        load_model_config(catalog(tmp_path, [MODEL], **overrides))


def test_committed_catalog_has_current_requested_families_and_bounded_counts():
    models = load_model_config(Path(__file__).resolve().parents[1] / "config/models.json")
    counts = Counter(model["provider"] for model in models)
    assert counts == {"anthropic": 4, "openai": 4, "google": 3}
    assert len(models) == 11
    ids = {model["model"] for model in models}
    assert {"claude-sonnet-5", "claude-opus-5", "claude-fable-5-1", "gpt-6-astra", "gpt-5.6-sol", "gemini-3.8-flash"} <= ids
    assert all(model["input_per_m"] is not None and model["output_per_m"] is not None for model in models)


def test_unavailable_gemini_reference_is_preserved_but_disabled():
    path = Path(__file__).resolve().parents[1] / "config/models.json"
    records = json.loads(path.read_text())["models"]
    model = next(model for model in records if model["id"] == "gemini-2.5-flash-lite")
    assert model["enabled"] is False
    assert "404" in model["notes"]
    assert "2026-09-07" in model["notes"]
    assert model["id"] not in {model["id"] for model in load_model_config(path)}
