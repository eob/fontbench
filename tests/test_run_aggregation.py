"""Frozen-release reporting combines dated measurements without selecting better answers."""

import hashlib
import json

from PIL import Image
import pytest

from baseline import build_page, reporting
from baseline.evaluator import dataset_fingerprint, evaluation_protocol_fingerprint
from baseline.model_config import load_model_config


@pytest.fixture
def release_history(tmp_path):
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (80, 50), "white").save(image_path)
    items = [{
        "taskId": f"task-{index}", "fontId": "arial", "fontName": "Arial", "aliases": [],
        "category": "non-serif", "weight": "regular", "modifier": "regular",
        "kerning": "normal", "lineHeight": "normal", "widthId": "narrow", "widthPx": 220,
        "imageFilename": "sample.png", "imagePath": str(image_path), "pangram": "Fixture text.",
    } for index in range(3)]
    (tmp_path / "manifest.json").write_text(json.dumps(items))
    release = {
        "schema_version": 1, "benchmark_version": "1.0.0", "dataset_manifest": "manifest.json",
        "dataset_git_path": "manifest.json", "dataset_git_commit": "a" * 40,
        "dataset_fingerprint": dataset_fingerprint(items),
        "evaluation_protocol_fingerprint": evaluation_protocol_fingerprint(), "expected_task_count": 3,
    }
    config_path = tmp_path / "models.json"
    config_path.write_text(json.dumps({"version": 1, "verified_at": "2026-09-08", "models": [{
        "id": "arbitrary-model", "provider": "google", "model": "custom-model", "display_name": "Custom model",
        "api_key_env": "TEST_API_KEY", "source_url": "https://example.com/model", "max_output_tokens": 1024,
    }]}))
    config = load_model_config(config_path)[0]
    config_path.unlink()
    return tmp_path, release, items, config


def write_run(history, run_id, task_indices, *, correct=True, day=1, config=None, invalid=False):
    from baseline.releases import model_config_fingerprint

    root, release, items, default_config = history
    config = dict(config or default_config)
    created_at = f"2026-09-{day:02d}T10:00:00Z"
    updated_at = f"2026-09-{day:02d}T12:00:00Z"
    tasks = [{
        "task_id": items[index]["taskId"], "font_id": "arial", "target_canonical": "Arial", "target_aliases": [],
        "category": "non-serif", "weight": "regular", "modifier": "regular", "kerning": "normal",
        "line_height": "normal", "width_id": "narrow", "width_px": 220,
        "model_name": config["model"], "provider": config["provider"],
        "recorded_at": f"2026-09-{day:02d}T11:00:00Z", "latency_sec": 1.0,
        "error_kind": "invalid_response" if invalid else None,
        "error": "Invalid answer" if invalid else None,
        **{f"{field}_correct": correct and not invalid for field in reporting.DIMENSIONS},
    } for index in task_indices]
    identity = {key: release[key] for key in (
        "schema_version", "benchmark_version", "dataset_git_commit", "dataset_git_path",
        "dataset_fingerprint", "evaluation_protocol_fingerprint", "expected_task_count",
    )}
    shared = {**identity, "run_id": run_id, "created_at": created_at, "updated_at": updated_at,
              "runner_git_commit": "b" * 40, "runner_git_dirty": False, "mock": False, "grading_version": "3"}
    model_state = {"model_config": config, "model_config_fingerprint": model_config_fingerprint(config),
                   "model": config["model"], "provider": config["provider"], "max_output_tokens": config["max_output_tokens"],
                   "status": "partial", "cost_usd": None, "completed": len(tasks)}
    summary = {**shared, "models": {config["id"]: model_state}}
    card = {**shared, **model_state, "model_id": config["id"], "model_name": config["model"],
            "tasks": tasks, "total_tasks": len(tasks), "status": "complete" if len(tasks) == len(items) else "partial",
            "cohort_fingerprint": hashlib.sha256(json.dumps(sorted(task["task_id"] for task in tasks)).encode()).hexdigest()}
    directory = root / "runs" / "1.0.0" / run_id
    directory.mkdir(parents=True)
    (directory / "summary.json").write_text(json.dumps(summary))
    (directory / "run.json").write_text(json.dumps({
        **shared, "invocations": [{"started_at": created_at, "updated_at": updated_at,
                                    "runner_git_commit": "b" * 40, "runner_git_dirty": False,
                                    "models": [config], "status": "partial"}],
    }))
    (directory / f'scorecard_{config["id"]}.json').write_text(json.dumps(card))
    return directory, summary, card


def aggregate(history):
    root, release, items, _ = history
    return reporting.aggregate_release_runs(release, items, root / "runs")


def test_dated_partial_runs_accumulate_without_a_current_model_catalog(release_history):
    write_run(release_history, "first", [0], day=1)
    write_run(release_history, "second", [1, 2], day=8)
    root, release, items, _ = release_history
    report = reporting.aggregate_release_runs(release, items, root / "runs")
    model = report["models"][0]
    assert model["completed"] == 3
    assert model["status"] == "complete"
    assert model["metrics"]["composite"] == 1
    assert {origin["run_id"] for origin in model["origins"]} == {"first", "second"}
    assert model["duplicate_count"] == 0
    assert report["warnings"] == []


@pytest.mark.parametrize("invalid", [False, True])
def test_first_recorded_answer_wins_even_when_later_answer_is_better(release_history, invalid):
    write_run(release_history, "z-early", [0], day=1, correct=False, invalid=invalid)
    write_run(release_history, "a-later", [0, 1], day=8, correct=True)
    report = aggregate(release_history)
    model = report["models"][0]
    assert model["completed"] == 2
    assert model["metrics"]["composite"] == 0.5
    assert model["duplicate_count"] == 1
    tasks = report["tasks_by_model"][model["id"]]
    assert tasks[0]["source_run_id"] == "z-early"
    assert tasks[0]["recorded_at"] == "2026-09-01T11:00:00Z"
    assert model["invalid_response_count"] == int(invalid)
    assert aggregate(release_history) == report


def test_tied_recording_times_use_run_id_and_never_score(release_history):
    write_run(release_history, "z-run", [0], correct=True)
    write_run(release_history, "a-run", [0], correct=False)
    report = aggregate(release_history)
    model = report["models"][0]
    assert model["metrics"]["composite"] == 0
    assert report["tasks_by_model"][model["id"]][0]["source_run_id"] == "a-run"


def test_inference_changes_split_models_but_catalog_and_pricing_changes_do_not(release_history):
    config = release_history[3]
    write_run(release_history, "initial", [0])
    write_run(release_history, "renamed", [1], day=2, config={**config, "id": "new-name", "input_per_m": 4})
    write_run(release_history, "larger-cap", [2], day=3, config={**config, "max_output_tokens": 2048})
    report = aggregate(release_history)
    assert sorted(model["completed"] for model in report["models"]) == [1, 2]
    combined = next(model for model in report["models"] if model["completed"] == 2)
    assert {origin["model_config"]["id"] for origin in combined["origins"]} == {"arbitrary-model", "new-name"}


@pytest.mark.parametrize(("file", "field", "value"), [
    ("summary", "benchmark_version", "0.9.0"), ("summary", "dataset_git_commit", "c" * 40),
    ("summary", "dataset_fingerprint", "wrong"), ("summary", "evaluation_protocol_fingerprint", "wrong"),
    ("summary", "mock", True), ("summary", "mock", None), ("summary", "run_id", "foreign"),
    ("summary", "created_at", "yesterday"), ("card", "benchmark_version", None),
    ("card", "model_config_fingerprint", "wrong"), ("card", "mock", True),
])
def test_incompatible_ledger_is_excluded_while_valid_peer_survives(release_history, file, field, value):
    write_run(release_history, "valid", [0])
    directory, summary, card = write_run(release_history, "invalid", [1])
    data = summary if file == "summary" else card
    data[field] = value
    filename = "summary.json" if file == "summary" else "scorecard_arbitrary-model.json"
    (directory / filename).write_text(json.dumps(data))
    report = aggregate(release_history)
    assert report["models"][0]["completed"] == 1
    assert {origin["run_id"] for origin in report["models"][0]["origins"]} == {"valid"}
    assert report["warnings"]
    assert report["excluded_runs"]


@pytest.mark.parametrize(("field", "value"), [("recorded_at", None), ("recorded_at", "2026-09-01T11:00:00"),
                                              ("target_canonical", "Wrong font"), ("error_kind", "rate_limit")])
def test_invalid_task_identity_or_chronology_cannot_enter_aggregate(release_history, field, value):
    directory, _, card = write_run(release_history, "invalid", [0])
    card["tasks"][0][field] = value
    (directory / "scorecard_arbitrary-model.json").write_text(json.dumps(card))
    report = aggregate(release_history)
    assert report["models"] == []
    assert report["warnings"]


def test_historical_unversioned_results_are_explicitly_excluded(release_history):
    directory, _, _ = write_run(release_history, "old", [0])
    directory.rename(release_history[0] / "runs" / "historical")
    report = aggregate(release_history)
    assert report["models"] == []
    assert any("historical" in entry["path"] for entry in report["excluded_runs"])


def test_release_page_shows_version_commit_origins_and_shared_cohort(release_history, monkeypatch):
    function = build_page.build_release_page
    from baseline import releases

    root, release, items, config = release_history
    monkeypatch.setattr(releases, "load_release", lambda version, **kwargs: release)
    monkeypatch.setattr(releases, "validate_release", lambda descriptor, **kwargs: items)
    monkeypatch.setattr(build_page, "validate_dataset", lambda path: {"valid": True, "errors": []})
    directory, _, _ = write_run(release_history, "first", [0])
    attempts = '{"task_id":"task-0","cost_usd":0.1}\n'
    (directory / "attempts.jsonl").write_text(attempts)
    write_run(release_history, "second", [0, 1], day=2, config={**config, "model": "other-model"})
    report = function("1.0.0", root / "runs", root / "site", root=root)
    html = (root / "site/index.html").read_text()
    assert report["benchmark_version"] == "1.0.0"
    assert report["comparison"]["count"] == 1
    assert len(report["models"]) == 2
    assert "FontBench 1.0.0" in html
    assert "https://github.com/eob/fontbench/commit/" + release["dataset_git_commit"] in html
    assert "first" in html and "second" in html
    assert "2026-09-01" in html and "2026-09-02" in html
    assert (root / "site/runs/first/attempts.jsonl").read_text() == attempts
    assert "all run attempts, including repeats" in html


def test_duplicate_order_uses_aware_task_times_instead_of_run_start_or_string_order(release_history):
    early_dir, _, early = write_run(release_history, "a-started-first", [0], correct=True)
    later_dir, _, later = write_run(release_history, "z-recorded-first", [0], correct=False)
    early["tasks"][0]["recorded_at"] = "2026-09-01T11:30:00+00:00"
    later["tasks"][0]["recorded_at"] = "2026-09-01T14:00:00+03:00"
    (early_dir / "scorecard_arbitrary-model.json").write_text(json.dumps(early))
    (later_dir / "scorecard_arbitrary-model.json").write_text(json.dumps(later))
    report = aggregate(release_history)
    model = report["models"][0]
    assert model["metrics"]["composite"] == 0
    chosen = report["tasks_by_model"][model["id"]][0]
    assert chosen["source_run_id"] == "z-recorded-first"
    assert chosen["recorded_at"] == "2026-09-01T11:00:00Z"


def test_duplicate_measurements_keep_all_spending_provenance(release_history):
    for run_id, day, cost in [("first", 1, 0.25), ("repeated", 2, 0.75)]:
        directory, summary, _ = write_run(release_history, run_id, [0], day=day)
        summary["models"]["arbitrary-model"].update(cost_usd=cost, attempted_tasks=1)
        summary.update(spent_cost_usd=cost, cost_incomplete=False)
        (directory / "summary.json").write_text(json.dumps(summary))
    model = aggregate(release_history)["models"][0]
    assert model["completed"] == 1
    assert model["duplicate_count"] == 1
    assert model["cost_usd"] == 1
    assert sum(origin["cost_usd"] for origin in model["origins"]) == 1
    assert sum(origin["attempted_tasks"] for origin in model["origins"]) == 2


def test_empty_compatible_scorecards_preserve_pending_configuration(release_history):
    write_run(release_history, "pending", [])
    model = aggregate(release_history)["models"][0]
    assert model["completed"] == 0
    assert model["status"] == "pending"
    assert model["metrics"]["composite"] is None
    assert model["origins"][0]["run_id"] == "pending"


def test_actual_runner_ledgers_aggregate_without_provider_requests(release_history, monkeypatch):
    from baseline import runner
    from baseline.evaluator import BaselineEvaluator
    from baseline.providers import PredictionResponse

    root, release, items, config = release_history
    config_path = root / "runtime-models.json"
    config_path.write_text(json.dumps({"version": 1, "verified_at": "2026-09-08", "models": [config]}))
    monkeypatch.setattr(runner, "load_release", lambda version: release)
    monkeypatch.setattr(runner, "release_manifest_path", lambda descriptor: root / "manifest.json")
    monkeypatch.setattr(runner, "validate_release", lambda descriptor, path: list(items))
    monkeypatch.setattr("baseline.validate_dataset.require_valid_dataset", lambda path: {"valid": True})
    prediction = {"font": "Arial", "category": "non-serif", "weight": "regular", "modifier": "regular",
                  "kerning": "normal", "line_height": "normal"}
    monkeypatch.setattr(BaselineEvaluator, "predict_image", lambda *args: PredictionResponse(
        json.dumps(prediction), prediction, input_tokens=1, output_tokens=1, request_attempts=1))
    runner.run_benchmark(release="1.0.0", config_path=config_path, output_dir=root / "runs",
                         run_id="runner", budget_usd=None, max_tasks=2, concurrency=1)
    report = aggregate(release_history)
    assert report["warnings"] == []
    assert report["models"][0]["completed"] == 2
    assert report["models"][0]["metrics"]["composite"] == 1
    assert report["runs"][0]["has_attempt_ledger"] is True


@pytest.mark.parametrize(("record", "field", "value"), [
    ("run", "benchmark_version", "0.9.0"), ("run", "created_at", "2026-08-31T10:00:00Z"),
    ("run", "invocations", []), ("summary", "runner_git_commit", "short"),
    ("summary", "runner_git_dirty", "false"), ("card", "runner_git_commit", "c" * 40),
    ("state", "completed", 999), ("state", "completed", True),
])
def test_inconsistent_run_history_and_code_provenance_are_excluded(release_history, record, field, value):
    directory, summary, card = write_run(release_history, "invalid", [0])
    if record == "run":
        data = json.loads((directory / "run.json").read_text())
        filename = "run.json"
    elif record == "card":
        data, filename = card, "scorecard_arbitrary-model.json"
    else:
        data, filename = summary, "summary.json"
    target = data["models"]["arbitrary-model"] if record == "state" else data
    target[field] = value
    (directory / filename).write_text(json.dumps(data))
    report = aggregate(release_history)
    assert report["models"] == []
    assert report["warnings"]


def test_missing_run_metadata_is_excluded_and_missing_attempt_history_is_explicit(release_history):
    missing, _, _ = write_run(release_history, "missing-run", [0])
    (missing / "run.json").unlink()
    write_run(release_history, "missing-attempts", [1])
    report = aggregate(release_history)
    assert report["models"][0]["completed"] == 1
    assert report["runs"][0]["attempt_history_status"] == "missing"
    assert report["excluded_runs"]


def test_explicitly_unavailable_code_identity_and_multiple_invocations_are_retained(release_history):
    directory, summary, card = write_run(release_history, "resumed", [0])
    summary.update(runner_git_commit=None, runner_git_dirty=None)
    metadata = json.loads((directory / "run.json").read_text())
    metadata["invocations"].append({**metadata["invocations"][0], "runner_git_commit": None, "runner_git_dirty": None})
    (directory / "summary.json").write_text(json.dumps(summary))
    (directory / "run.json").write_text(json.dumps(metadata))
    report = aggregate(release_history)
    assert report["models"][0]["completed"] == 1
    assert len(report["runs"][0]["invocations"]) == 2
    assert report["runs"][0]["invocations"][0]["runner_git_commit"] == card["runner_git_commit"]
    assert report["warnings"] == []


@pytest.mark.parametrize(("field", "value"), [("started_at", "2026-09-01T11:30:00Z"),
                                              ("updated_at", "2026-09-01T10:30:00Z")])
def test_task_must_fall_inside_an_invocation_of_its_recorded_configuration(release_history, field, value):
    directory, _, _ = write_run(release_history, "invalid", [0])
    metadata_path = directory / "run.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["invocations"][0][field] = value
    metadata_path.write_text(json.dumps(metadata))
    report = aggregate(release_history)
    assert report["models"] == []
    assert report["warnings"]


def test_unclassified_transport_errors_cannot_be_scored_as_final_answers(release_history):
    directory, _, card = write_run(release_history, "invalid", [0])
    card["tasks"][0]["error"] = "TimeoutError: connection interrupted"
    (directory / "scorecard_arbitrary-model.json").write_text(json.dumps(card))
    report = aggregate(release_history)
    assert report["models"] == []
    assert report["warnings"]
