"""Regression tests for trustworthy benchmark exports."""

import json
from datetime import datetime

import pytest

from baseline.export_structured import build_structured_benchmark


def write_scorecard(tmp_path, name="example", **overrides):
    data = {
        "model_name": name, "timestamp": "2025-01-02 03:04:05 UTC",
        "total_tasks": 1000, "overall_composite_score": 0.5,
        "avg_latency_sec": 1.0,
        "tasks": [{"task_id": f"arial-{i}", "target_canonical": "Arial", "font_correct": True} for i in range(1000)],
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
    write_scorecard(tmp_path, "slightly-better", overall_composite_score=0.50049)
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
    write_scorecard(tmp_path, pricing={"input_per_m": 2.0, "output_per_m": 10.0})
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


@pytest.mark.parametrize("version", [None, "2"])
def test_export_identifies_legacy_and_corrected_grading(tmp_path, version):
    overrides = {"grading_version": version} if version else {}
    write_scorecard(tmp_path, **overrides)
    model = build_structured_benchmark(str(tmp_path))["models"][0]
    assert model["grading_version"] == (version or "legacy")


def test_empty_summary_does_not_invent_a_dataset_size(tmp_path):
    assert build_structured_benchmark(str(tmp_path))["total_tasks_per_model"] is None


def test_mixed_run_sizes_are_not_reported_as_one_shared_dataset_size(tmp_path):
    write_scorecard(tmp_path)
    write_scorecard(tmp_path, "small", total_tasks=1, expected_task_count=1,
                    tasks=[{"task_id": "arial-1", "target_canonical": "Arial"}])
    assert build_structured_benchmark(str(tmp_path))["total_tasks_per_model"] is None


@pytest.mark.parametrize("difference", ["grading_version", "task_ids"])
def test_pareto_never_compares_different_grading_rules_or_task_sets(tmp_path, difference):
    write_scorecard(tmp_path, "fast", grading_version="2", overall_composite_score=0.9)
    overrides = {"grading_version": "2", "overall_composite_score": 0.1, "avg_latency_sec": 2.0}
    if difference == "grading_version":
        overrides["grading_version"] = "legacy"
    else:
        overrides["tasks"] = [{"task_id": f"other-{i}", "target_canonical": "Arial"} for i in range(1000)]
    write_scorecard(tmp_path, "slow", **overrides)
    assert set(build_structured_benchmark(str(tmp_path))["pareto_frontier"]) == {"fast", "slow"}


def test_new_scorecards_preserve_provider_and_dataset_identity(tmp_path):
    write_scorecard(tmp_path, 'model-a', provider='anthropic', dataset_fingerprint='pixels-a')
    model = build_structured_benchmark(str(tmp_path))['models'][0]
    assert model['provider'] == 'anthropic'
    assert model['dataset_fingerprint'] == 'pixels-a'


def test_same_task_ids_with_different_pixels_are_not_comparable(tmp_path):
    write_scorecard(tmp_path, 'fast', dataset_fingerprint='pixels-a', overall_composite_score=0.9)
    write_scorecard(tmp_path, 'slow', dataset_fingerprint='pixels-b', overall_composite_score=0.1, avg_latency_sec=2.0)
    assert set(build_structured_benchmark(str(tmp_path))['pareto_frontier']) == {'fast', 'slow'}
