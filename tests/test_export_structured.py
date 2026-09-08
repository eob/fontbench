"""Regression tests for trustworthy benchmark exports."""

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime

import pytest

from baseline.export_structured import build_structured_benchmark
from baseline.evaluator import evaluation_protocol_fingerprint


FIELDS = ["font", "category", "weight", "modifier", "kerning", "line_height"]


def write_scorecard(tmp_path, name="example", **overrides):
    total = overrides.get("total_tasks", 1000)
    proportion = overrides.get("overall_composite_score", 0.5)
    defaults = {"target_canonical": "Arial", "category": "non-serif", "weight": "regular", "modifier": "regular",
                "kerning": "normal", "line_height": "normal", "width_id": "narrow",
                "latency_sec": overrides.get("avg_latency_sec", 1.0)}
    tasks = overrides.pop("tasks", None)
    if tasks is None:
        tasks = [{"task_id": f"arial-{i}", **{f"{field}_correct": i < round(total * proportion) for field in FIELDS}} for i in range(total)]
    tasks = [{**defaults, **{f"{field}_correct": True for field in FIELDS}, **task} for task in tasks]
    data = {
        "model_name": name, "timestamp": "2025-01-02 03:04:05 UTC", "mock": False,
        "total_tasks": total, "expected_task_count": total, "status": "complete",
        "grading_version": "3", "dataset_fingerprint": "fixture-pixels",
        "evaluation_protocol_fingerprint": evaluation_protocol_fingerprint(),
        "cohort_fingerprint": hashlib.sha256(json.dumps(sorted(task["task_id"] for task in tasks)).encode()).hexdigest(),
        "overall_composite_score": proportion, "avg_latency_sec": 1.0, "tasks": tasks,
    }
    data.update(overrides)
    (tmp_path / f"scorecard_{name}.json").write_text(json.dumps(data))
    return data


def test_explicit_mock_scorecards_are_excluded_independent_of_filename(tmp_path):
    write_scorecard(tmp_path, mock=True)
    assert build_structured_benchmark(str(tmp_path))["models"] == []


@pytest.mark.parametrize("tasks", [[], [{"task_id": "duplicate", "target_canonical": "Arial"}] * 1000])
def test_incomplete_or_duplicate_task_results_are_excluded(tmp_path, tasks):
    write_scorecard(tmp_path, tasks=tasks)
    assert build_structured_benchmark(str(tmp_path))["models"] == []


def test_run_completeness_uses_recorded_manifest_size(tmp_path):
    write_scorecard(tmp_path, total_tasks=1, expected_task_count=1,
                    tasks=[{"task_id": "arial-1", "target_canonical": "Arial"}])
    assert len(build_structured_benchmark(str(tmp_path))["models"]) == 1


def test_limited_runs_are_excluded_even_above_historical_task_count(tmp_path):
    write_scorecard(tmp_path, expected_task_count=2000)
    assert build_structured_benchmark(str(tmp_path))["models"] == []


def test_pareto_frontier_depends_on_measured_score_and_latency(tmp_path):
    write_scorecard(tmp_path, "gemini-3.5-flash", overall_composite_score=0.4, avg_latency_sec=2.0)
    write_scorecard(tmp_path, "custom-better", overall_composite_score=0.8, avg_latency_sec=1.0)
    write_scorecard(tmp_path, "custom-fast", overall_composite_score=0.2, avg_latency_sec=0.5)
    data = build_structured_benchmark(str(tmp_path))
    assert set(data["pareto_frontier"]) == {"custom-better", "custom-fast"}
    assert not next(m for m in data["models"] if m["model_id"] == "gemini-3.5-flash")["is_pareto_frontier"]


def test_pareto_comparison_happens_before_display_rounding(tmp_path):
    write_scorecard(tmp_path, "slightly-better", overall_composite_score=0.50149)
    write_scorecard(tmp_path, "slightly-worse", overall_composite_score=0.50041)
    assert build_structured_benchmark(str(tmp_path))["pareto_frontier"] == ["slightly-better"]


def test_unrecorded_prices_and_performance_notes_are_not_invented(tmp_path):
    write_scorecard(tmp_path, "gemini-3.5-flash")
    model = build_structured_benchmark(str(tmp_path))["models"][0]
    assert model["pricing"]["input_per_m"] is None
    assert model["pricing"]["output_per_m"] is None
    assert model["pricing"]["estimated_run_cost_usd"] is None
    assert model["notes"] == ""


def test_recorded_pricing_is_used_for_estimates(tmp_path):
    write_scorecard(tmp_path, pricing={"input_per_m": 2.0, "output_per_m": 10.0},
                    tasks=[{"task_id": f"arial-{i}", "input_tokens": 750, "output_tokens": 60} for i in range(1000)])
    model = build_structured_benchmark(str(tmp_path))["models"][0]
    assert model["pricing"]["input_per_m"] == 2.0
    assert model["pricing"]["output_per_m"] == 10.0
    assert model["pricing"]["estimated_run_cost_usd"] == 2.1


def test_evaluation_dates_come_from_saved_run_timestamps(tmp_path):
    write_scorecard(tmp_path)
    data = build_structured_benchmark(str(tmp_path))
    assert data["eval_date"] == "2025-01-02"
    assert data["models"][0]["evaluated_at"] == "2025-01-02 03:04:05 UTC"
    assert datetime.fromisoformat(data["generated_at"]).tzinfo is not None


@pytest.mark.parametrize("version", [None, "2", "3"])
def test_export_identifies_legacy_and_corrected_grading(tmp_path, version):
    write_scorecard(tmp_path, grading_version=version)
    models = build_structured_benchmark(str(tmp_path))["models"]
    assert len(models) == (1 if version == "3" else 0)


def test_empty_summary_does_not_invent_a_dataset_size(tmp_path):
    assert build_structured_benchmark(str(tmp_path))["total_tasks_per_model"] is None


def test_mixed_run_sizes_are_not_reported_as_one_shared_dataset_size(tmp_path):
    write_scorecard(tmp_path)
    write_scorecard(tmp_path, "small", total_tasks=1, expected_task_count=1,
                    tasks=[{"task_id": "arial-1", "target_canonical": "Arial"}])
    assert build_structured_benchmark(str(tmp_path))["total_tasks_per_model"] is None


@pytest.mark.parametrize("difference", ["grading_version", "task_ids"])
def test_pareto_never_compares_different_grading_rules_or_task_sets(tmp_path, difference):
    write_scorecard(tmp_path, "fast", grading_version="3", overall_composite_score=0.9)
    overrides = {"grading_version": "3", "overall_composite_score": 0.1, "avg_latency_sec": 2.0}
    if difference == "grading_version":
        overrides["grading_version"] = "legacy"
    else:
        overrides["tasks"] = [{"task_id": f"other-{i}", "target_canonical": "Arial"} for i in range(1000)]
    write_scorecard(tmp_path, "slow", **overrides)
    assert set(build_structured_benchmark(str(tmp_path))["pareto_frontier"]) == ({"fast"} if difference == "grading_version" else {"fast", "slow"})


def test_new_scorecards_preserve_provider_and_dataset_identity(tmp_path):
    write_scorecard(tmp_path, 'model-a', provider='anthropic', dataset_fingerprint='pixels-a')
    model = build_structured_benchmark(str(tmp_path))['models'][0]
    assert model['provider'] == 'anthropic'
    assert model['dataset_fingerprint'] == 'pixels-a'


def test_same_task_ids_with_different_pixels_are_not_comparable(tmp_path):
    write_scorecard(tmp_path, 'fast', dataset_fingerprint='pixels-a', overall_composite_score=0.9)
    write_scorecard(tmp_path, 'slow', dataset_fingerprint='pixels-b', overall_composite_score=0.1, avg_latency_sec=2.0)
    assert set(build_structured_benchmark(str(tmp_path))['pareto_frontier']) == {'fast', 'slow'}


def test_export_recomputes_metrics_from_task_outcomes(tmp_path):
    tasks = [{
        'task_id': 'arial-1', 'target_canonical': 'Arial',
        **{f'{field}_correct': False for field in ['font', 'category', 'weight', 'modifier', 'kerning', 'line_height']},
    }]
    write_scorecard(tmp_path, total_tasks=1, expected_task_count=1, tasks=tasks, overall_composite_score=1.0)
    model = build_structured_benchmark(str(tmp_path))['models'][0]
    assert model['overall_composite_score'] == 0.0


def test_export_font_count_comes_from_observed_data(tmp_path):
    write_scorecard(tmp_path)
    report = build_structured_benchmark(str(tmp_path))
    assert report['total_fonts'] == 1
    assert {font['name'] for font in report['taxonomies']['fonts']} == {'Arial'}


@pytest.mark.parametrize("field", ["mock", "dataset_fingerprint", "evaluation_protocol_fingerprint", "cohort_fingerprint"])
def test_unproven_scorecards_are_excluded(tmp_path, field):
    card = write_scorecard(tmp_path)
    card.pop(field)
    (tmp_path / "scorecard_example.json").write_text(json.dumps(card))
    report = build_structured_benchmark(str(tmp_path))
    assert report["models"] == []
    assert report["warnings"]


@pytest.mark.parametrize("value", [True, -1, float("nan"), float("inf"), None])
def test_invalid_latency_is_excluded(tmp_path, value):
    write_scorecard(tmp_path, avg_latency_sec=value)
    assert build_structured_benchmark(str(tmp_path))["models"] == []


def test_cost_is_not_estimated_from_invented_token_counts(tmp_path):
    write_scorecard(tmp_path, pricing={"input_per_m": 2.0, "output_per_m": 10.0})
    assert build_structured_benchmark(str(tmp_path))["models"][0]["pricing"]["estimated_run_cost_usd"] is None


def test_unknown_fonts_are_preserved_in_breakdowns(tmp_path):
    write_scorecard(tmp_path, total_tasks=1, tasks=[{"task_id": "unknown", "target_canonical": "New Typeface"}])
    report = build_structured_benchmark(str(tmp_path))
    assert report["models"][0]["per_font"][0]["font"] == "New Typeface"
    assert report["total_fonts"] == 1


def test_corrupt_json_is_excluded_instead_of_breaking_other_exports(tmp_path):
    (tmp_path / "scorecard_broken.json").write_text("{unfinished")
    write_scorecard(tmp_path)
    report = build_structured_benchmark(str(tmp_path))
    assert len(report["models"]) == 1
    assert report["warnings"]


@pytest.mark.parametrize(("field", "value"), [
    ("category", {}), ("category", []), ("category", None), ("category", False),
    ("category", ""), ("category", "   "),
    ("weight", {}), ("modifier", []), ("kerning", None),
    ("line_height", False), ("width_id", 0), ("target_canonical", "   "),
])
def test_malformed_export_task_metadata_preserves_valid_peer(tmp_path, field, value):
    write_scorecard(tmp_path, "valid", total_tasks=1)
    write_scorecard(tmp_path, "broken", total_tasks=1, tasks=[{"task_id": "one", field: value}])
    report = build_structured_benchmark(str(tmp_path))
    assert [model["model_id"] for model in report["models"]] == ["valid"]
    assert report["models"][0]["total_tasks"] == 1
    assert len(report["warnings"]) == 1


@pytest.mark.parametrize("value", [{}, [], None, False, 0, "", "   "])
def test_malformed_export_model_id_preserves_valid_peer(tmp_path, value):
    write_scorecard(tmp_path, "valid", total_tasks=1)
    write_scorecard(tmp_path, "broken", total_tasks=1, model_id=value)
    report = build_structured_benchmark(str(tmp_path))
    assert [model["model_id"] for model in report["models"]] == ["valid"]
    assert len(report["warnings"]) == 1


def test_export_preserves_explicit_and_omitted_model_ids(tmp_path):
    write_scorecard(tmp_path, "default", total_tasks=1)
    write_scorecard(tmp_path, "named", total_tasks=1, model_id="custom-id")
    report = build_structured_benchmark(str(tmp_path))
    assert {model["model_id"] for model in report["models"]} == {"default", "custom-id"}
    assert report["warnings"] == []


def test_legacy_export_is_explicitly_unversioned(tmp_path):
    write_scorecard(tmp_path, total_tasks=1)
    report = build_structured_benchmark(str(tmp_path))
    assert report["version"] is None
    assert report["benchmark_version"] is None
    assert report["schema_version"] == 1


def test_legacy_cli_requires_explicit_paths_and_preserves_historical_output(tmp_path):
    directory = tmp_path / "results"
    directory.mkdir()
    historical = directory / "fontbench_summary.json"
    historical.write_text("Historical results must stay intact.\n")
    result = subprocess.run([sys.executable, "-m", "baseline.export_structured"], cwd=tmp_path,
                            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
                            capture_output=True, text=True)
    assert historical.read_text() == "Historical results must stay intact.\n"
    assert result.returncode != 0
    assert "--results-dir" in result.stderr and "--output" in result.stderr


def test_legacy_cli_writes_only_requested_output(tmp_path):
    directory = tmp_path / "input"
    directory.mkdir()
    write_scorecard(directory, total_tasks=1)
    historical_dir = tmp_path / "results"
    historical_dir.mkdir()
    historical = historical_dir / "fontbench_summary.json"
    historical.write_text("Historical results must stay intact.\n")
    output = tmp_path / "explicit" / "summary.json"
    result = subprocess.run([sys.executable, "-m", "baseline.export_structured", "--results-dir", str(directory),
                             "--output", str(output)], cwd=tmp_path,
                            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert output.exists()
    assert len(json.loads(output.read_text())["models"]) == 1
    assert historical.read_text() == "Historical results must stay intact.\n"
