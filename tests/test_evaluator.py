"""Offline regression tests for baseline grading, requests, and saved results."""

import json
from unittest.mock import Mock

import httpx
import pytest
from PIL import Image
from pydantic import ValidationError

from baseline import cli
from baseline.evaluator import BaselineEvaluator, TypographicPrediction, grade_font_prediction
from baseline.providers import PredictionResponse


PREDICTION = {
    "font": "Arial",
    "category": "non-serif",
    "weight": "regular",
    "modifier": "regular",
    "kerning": "normal",
    "line_height": "normal",
}


@pytest.fixture
def task(tmp_path):
    image = tmp_path / "sample.png"
    Image.new("RGB", (4, 4), "white").save(image)
    return {
        "taskId": "arial-1", "fontId": "arial", "fontName": "Arial",
        "aliases": ["Arial MT"], "category": "non-serif", "weight": "regular",
        "modifier": "regular", "kerning": "normal", "lineHeight": "normal",
        "widthId": "narrow", "widthPx": 220, "imagePath": str(image),
    }


@pytest.mark.parametrize("prediction,canonical,aliases,expected", [
    (" ARIAL! ", "Arial", [], True),
    ("Arial MT", "Arial", ["Arial MT"], True),
    ("Times", "Times New Roman", ["Times"], True),
    ("a", "Arial", [], False),
    ("Roboto", "Roboto Mono", [], False),
    ("Roboto Mono", "Roboto", [], False),
    ("Arial or Helvetica", "Arial", [], False),
    ("Arial", "Helvetica", ["!!!"], False),
    ("", "Arial", [], False),
])
def test_font_grading_requires_an_entire_canonical_name_or_alias(prediction, canonical, aliases, expected):
    assert grade_font_prediction(prediction, canonical, aliases) is expected


@pytest.mark.parametrize("prediction", [{}, {"font": "Arial"}, {**PREDICTION, "weight": "unknown"}, {**PREDICTION, "font": ""}])
def test_response_schema_requires_all_dimensions_and_valid_labels(prediction):
    with pytest.raises(ValidationError):
        TypographicPrediction.model_validate(prediction)


@pytest.mark.parametrize("prediction", [{}, {key: None for key in PREDICTION}, {key: "unknown" for key in PREDICTION}])
def test_missing_and_invalid_predictions_receive_no_default_credit(task, prediction):
    evaluator = BaselineEvaluator(mock=True)
    evaluator.predict_image = Mock(return_value=PredictionResponse(json.dumps(prediction), prediction))
    result = evaluator._eval_single_task(task, "prompt")
    assert result.composite_score == 0.0
    assert not any((result.font_correct, result.category_correct, result.weight_correct,
                    result.modifier_correct, result.kerning_correct, result.line_height_correct))


def test_valid_response_scores_all_dimensions(task):
    result = BaselineEvaluator(mock=True)._eval_single_task(task, "prompt")
    assert result.all_correct
    assert result.composite_score == 1.0


def test_api_error_scores_zero_and_preserves_failure(task):
    evaluator = BaselineEvaluator(mock=True)
    evaluator.predict_image = Mock(return_value=PredictionResponse("", error="ERROR: quota exceeded", error_kind="credits"))
    result = evaluator._eval_single_task(task, "prompt")
    assert result.error == "ERROR: quota exceeded"
    assert result.composite_score == 0.0


def remote_evaluator(monkeypatch, responses):
    monkeypatch.setenv("TEST_EVALUATOR_KEY", "fake-evaluator-key")
    evaluator = BaselineEvaluator(api_key_env="TEST_EVALUATOR_KEY")
    generate = Mock(side_effect=[
        httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": item}]}}]})
        if isinstance(item, str) else item for item in responses
    ])
    evaluator._client._http.post = generate
    monkeypatch.setattr("baseline.providers.time.sleep", lambda _: None)
    return evaluator, generate

@pytest.mark.parametrize("raw", ["[]", "null", "42", '"Arial"', "{}", "", "No answer", json.dumps({**PREDICTION, "weight": "unknown"})])
def test_malformed_api_responses_are_recorded_as_errors(task, monkeypatch, raw):
    evaluator, generate = remote_evaluator(monkeypatch, [raw] * 2)
    result = evaluator._eval_single_task(task, "prompt")
    assert result.error and result.error_kind == "invalid_response"
    assert result.composite_score == 0.0
    assert generate.call_count == 1


def test_transient_api_error_retries_and_closes_image(task, monkeypatch):
    evaluator, generate = remote_evaluator(monkeypatch, [httpx.ReadTimeout("temporary"), json.dumps(PREDICTION)])
    opened = []
    original_open = Image.open
    def track_open(path):
        img = original_open(path)
        opened.append(img)
        return img
    monkeypatch.setattr("baseline.providers.Image.open", track_open)
    response = evaluator.predict_image(task["imagePath"], "prompt")
    assert response.parsed == PREDICTION
    assert generate.call_count == 2
    assert all(img.fp is None for img in opened)


def test_missing_image_becomes_failed_task_without_request(task, monkeypatch):
    evaluator, generate = remote_evaluator(monkeypatch, [])
    task["imagePath"] += ".missing"
    result = evaluator._eval_single_task(task, "prompt")
    assert result.error
    assert result.composite_score == 0.0
    generate.assert_not_called()


@pytest.mark.parametrize("kwargs", [{"limit": -1}, {"concurrency": 0}, {"concurrency": -1}])
def test_invalid_run_parameters_are_rejected_before_evaluation(tmp_path, kwargs):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")
    with pytest.raises(ValueError):
        BaselineEvaluator(mock=True).evaluate_manifest(str(manifest), **kwargs)


def test_zero_limit_produces_an_empty_scorecard(task, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([task]))
    result = BaselineEvaluator(mock=True).evaluate_manifest(str(manifest), limit=0)
    assert result.total_tasks == 0
    assert result.overall_composite_score == 0.0
    assert result.task_results == []


def test_cli_mock_output_cannot_replace_a_live_scorecard(task, tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([task]))
    live = tmp_path / "scorecard_example.json"
    live.write_text('"existing live results"')
    monkeypatch.setattr("sys.argv", ["fontbench", "--mock", "--model", "example", "--manifest", str(manifest), "--output-dir", str(tmp_path)])
    cli.main()
    assert live.read_text() == '"existing live results"'
    saved = json.loads((tmp_path / "scorecard_mock_example.json").read_text())
    assert saved["mock"] is True
    assert saved["tasks"][0]["raw_prediction"]
    assert "error" in saved["tasks"][0]
    assert saved["tasks"][0]["image_path"] == task["imagePath"]


def test_manifest_images_are_resolved_relative_to_the_manifest(task, tmp_path, monkeypatch):
    monkeypatch.setattr("baseline.validate_dataset.require_valid_dataset", lambda path: {"valid": True})
    task.pop("imagePath")
    task["imageFilename"] = "sample.png"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([task]))
    evaluator, generate = remote_evaluator(monkeypatch, [json.dumps(PREDICTION)])
    result = evaluator.evaluate_manifest(str(manifest), concurrency=1)
    assert result.task_results[0].all_correct
    assert result.task_results[0].image_path == str(tmp_path / "sample.png")


def test_limited_scorecards_record_the_full_manifest_size(task, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([task, {**task, "taskId": "arial-2"}]))
    scorecard = BaselineEvaluator(mock=True).evaluate_manifest(str(manifest), limit=1)
    assert scorecard.total_tasks == 1
    assert scorecard.expected_task_count == 2


def test_new_scorecards_identify_the_corrected_grading_rules(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")
    assert BaselineEvaluator(mock=True).evaluate_manifest(str(manifest)).grading_version == "3"


def test_invalid_response_error_preserves_the_complete_raw_body(task, monkeypatch):
    raw = "An invalid response whose full body must remain available for debugging. " * 20
    evaluator, _ = remote_evaluator(monkeypatch, [raw] * 2)
    result = evaluator._eval_single_task(task, "prompt")
    assert raw in result.raw_prediction


@pytest.mark.parametrize("field", ["fontName", "category", "weight", "modifier", "kerning", "lineHeight"])
def test_incomplete_ground_truth_is_rejected_before_any_prediction(task, tmp_path, field):
    task.pop(field)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([task]))
    evaluator = BaselineEvaluator(mock=True)
    evaluator.predict_image = Mock(return_value=PredictionResponse(json.dumps(PREDICTION), PREDICTION))
    with pytest.raises(ValueError, match="typograph"):
        evaluator.evaluate_manifest(str(manifest))
    evaluator.predict_image.assert_not_called()


def test_noncanonical_ground_truth_labels_are_rejected(task, tmp_path):
    task["category"] = "sans-serif"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([task]))
    with pytest.raises(ValueError, match="typograph"):
        BaselineEvaluator(mock=True).evaluate_manifest(str(manifest))


@pytest.mark.parametrize("manifest_data", [{}, [None], [42]])
def test_malformed_manifest_structure_is_rejected(tmp_path, manifest_data):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(manifest_data))
    with pytest.raises(ValueError, match="[Mm]anifest"):
        BaselineEvaluator(mock=True).evaluate_manifest(str(manifest))


def test_duplicate_manifest_task_ids_are_rejected_before_any_prediction(task, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([task, task]))
    evaluator = BaselineEvaluator(mock=True)
    evaluator.predict_image = Mock(return_value=PredictionResponse(json.dumps(PREDICTION), PREDICTION))
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        evaluator.evaluate_manifest(str(manifest))
    evaluator.predict_image.assert_not_called()


def test_partial_parsed_responses_are_schema_failures_at_the_grading_boundary(task):
    evaluator = BaselineEvaluator(mock=True)
    evaluator.predict_image = Mock(return_value=PredictionResponse('{"font":"Arial"}', {'font': 'Arial'}))
    result = evaluator._eval_single_task(task, 'prompt')
    assert result.composite_score == 0
    assert result.error_kind == 'invalid_response'


def test_scorecard_marks_partial_cohort_and_invalid_model_answers(task):
    evaluator = BaselineEvaluator(mock=True)
    evaluator.predict_image = Mock(return_value=PredictionResponse('invalid', error='Invalid JSON', error_kind='invalid_response'))
    result = evaluator._eval_single_task(task, 'prompt')
    card = evaluator.score_results([result], expected_task_count=2)
    assert card.status == 'partial'
    assert card.invalid_response_count == 1
    assert card.overall_composite_score == 0
    assert card.cohort_fingerprint
    full = evaluator.score_results([result], expected_task_count=1)
    assert full.status == 'complete'
    assert full.cohort_fingerprint == card.cohort_fingerprint
    with pytest.raises(ValueError, match='[Dd]uplicate'):
        evaluator.score_results([result, result], expected_task_count=2)


@pytest.mark.parametrize('aliases', ['Arial', [None], ['  '], ['!!!'], 42])
def test_malformed_aliases_are_refused_before_evaluation(task, tmp_path, aliases):
    task['aliases'] = aliases
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps([task]))
    evaluator = BaselineEvaluator(mock=True)
    evaluator.predict_image = Mock()
    with pytest.raises(ValueError, match='[Aa]lias'):
        evaluator.evaluate_manifest(str(manifest))
    evaluator.predict_image.assert_not_called()


def test_live_evaluator_requires_valid_dataset_before_prediction(task, tmp_path, monkeypatch):
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps([task]))
    def refuse(path):
        raise ValueError('Dataset is not valid: audit evidence missing')
    monkeypatch.setattr('baseline.validate_dataset.require_valid_dataset', refuse)
    evaluator = BaselineEvaluator()
    evaluator.predict_image = Mock()
    try:
        with pytest.raises(ValueError, match='Dataset is not valid'):
            evaluator.evaluate_manifest(str(manifest))
        evaluator.predict_image.assert_not_called()
    finally:
        evaluator.close()
