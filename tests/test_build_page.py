"""Benchmark pages use real input images and label incomplete measurements."""

import base64
import json
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image
import pytest

from baseline.build_page import build_page
from baseline.runner import dataset_fingerprint
from baseline.evaluator import evaluation_protocol_fingerprint


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    monkeypatch.setattr("baseline.build_page.validate_dataset", lambda path: {"valid": True, "errors": []})
    samples = []
    for index in range(8):
        filename = f"sample-{index}.png"
        Image.new("RGB", (160, 60), (index * 30, 100, 150)).save(tmp_path / filename)
        samples.append({
            "taskId": f"task-{index}", "fontId": f"family-{index}", "fontName": f"Family {index}",
            "category": ["serif", "non-serif"][index % 2], "aliases": [],
            "weight": ["regular", "bold"][index % 2], "weightNumeric": [400, 700][index % 2],
            "modifier": ["regular", "italic"][index % 2],
            "kerning": ["normal", "loose"][index % 2], "lineHeight": ["normal", "tight"][index % 2],
            "widthId": "narrow", "widthPx": 220, "imageFilename": filename,
            "imagePath": str(tmp_path / filename), "pangram": "A fixture pangram.", "prompt": "Identify typography.",
        })
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(samples))
    config = tmp_path / "models.json"
    config.write_text(json.dumps({"version": 1, "verified_at": "2026-09-07", "models": [{
        "id": "test-model", "provider": "openai", "model": "exact-id", "display_name": "Test Model",
        "api_key_env": "OPENAI_API_KEY", "source_url": "https://developers.openai.com/api/docs/models",
        "input_per_m": 1, "output_per_m": 5,
    }]}))
    return manifest, samples, config


def write_scorecard(directory, samples, count=1, fingerprint=None):
    directory.mkdir()
    tasks = [{
        "task_id": sample["taskId"], "composite_score": 1.0, "all_correct": True,
        **{f"{field}_correct": True for field in ["font", "category", "weight", "modifier", "kerning", "line_height"]},
    } for sample in samples[:count]]
    (directory / "scorecard_test-model.json").write_text(json.dumps({
        "model_id": "test-model", "model_name": "exact-id", "provider": "openai", "max_output_tokens": 1024,
        "grading_version": "3", "mock": False,
        "evaluation_protocol_fingerprint": evaluation_protocol_fingerprint(),
        "cohort_fingerprint": hashlib.sha256(json.dumps(sorted(task["task_id"] for task in tasks)).encode()).hexdigest(),
        "status": "complete" if count == len(samples) else "partial",
        "dataset_fingerprint": fingerprint or dataset_fingerprint(samples), "tasks": tasks,
        "total_tasks": count, "expected_task_count": len(samples), "avg_latency_sec": 1.2,
    }))
    (directory / "summary.json").write_text(json.dumps({
        "evaluation_protocol_fingerprint": evaluation_protocol_fingerprint(),
        "status": "partial", "mock": False, "dataset_fingerprint": fingerprint or dataset_fingerprint(samples),
        "models": {"test-model": {"provider": "openai", "model": "exact-id", "max_output_tokens": 1024,
                                  "status": "running", "completed": count, "cost_usd": 0.01}},
    }))


def test_pending_page_does_not_invent_results(dataset, tmp_path):
    manifest, samples, config = dataset
    report = build_page(manifest, tmp_path / "missing-results", tmp_path / "site", config)
    assert report["models"][0]["completed"] == 0
    assert report["models"][0]["metrics"]["composite"] is None
    assert report["models"][0]["status"] == "pending"
    assert "Awaiting measured results" in (tmp_path / "site/index.html").read_text()


def test_partial_measurements_and_denominators_are_explicit(dataset, tmp_path):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / "results", samples)
    report = build_page(manifest, tmp_path / "results", tmp_path / "site", config)
    model = report["models"][0]
    assert model["completed"] == 1
    assert model["expected"] == 8
    assert model["status"] == "partial"
    assert model["metrics"]["composite"] == 1.0
    assert "1 / 8" in (tmp_path / "site/index.html").read_text()


def test_mismatched_dataset_scorecards_are_excluded(dataset, tmp_path):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / "results", samples, fingerprint="different-dataset")
    report = build_page(manifest, tmp_path / "results", tmp_path / "site", config)
    assert report["models"][0]["completed"] == 0
    assert report["models"][0]["cost_usd"] is None
    assert report["warnings"]


def test_scorecard_model_identity_must_match_config(dataset, tmp_path):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / "results", samples)
    data = json.loads(config.read_text())
    data["models"][0]["model"] = "different-live-model"
    config.write_text(json.dumps(data))
    report = build_page(manifest, tmp_path / "results", tmp_path / "site", config)
    assert report["models"][0]["completed"] == 0
    assert report["models"][0]["cost_usd"] is None
    assert report["warnings"]


@pytest.mark.parametrize(("field", "value"), [("model_id", "other-id"), ("provider", "google"), ("max_output_tokens", 2048)])
def test_scorecard_provider_id_and_output_cap_must_match(dataset, tmp_path, field, value):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / "results", samples)
    path = tmp_path / "results/scorecard_test-model.json"
    card = json.loads(path.read_text())
    card[field] = value
    path.write_text(json.dumps(card))
    report = build_page(manifest, tmp_path / "results", tmp_path / "site", config)
    assert report["models"][0]["completed"] == 0
    assert report["models"][0]["cost_usd"] is None


@pytest.mark.parametrize(("field", "value"), [("dataset_fingerprint", "different-dataset"), ("mock", True)])
def test_incompatible_summary_state_does_not_contaminate_matching_measurements(dataset, tmp_path, field, value):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / "results", samples)
    path = tmp_path / "results/summary.json"
    summary = json.loads(path.read_text())
    summary[field] = value
    summary["models"]["test-model"].update(status="paused", cost_usd=1234.5)
    path.write_text(json.dumps(summary))
    report = build_page(manifest, tmp_path / "results", tmp_path / "site", config)
    assert report["models"][0]["completed"] == 1
    assert report["models"][0]["cost_usd"] is None
    assert report["models"][0]["run_state"] == "pending"
    assert not report["mock"]
    assert report["warnings"]


def test_completed_run_and_estimated_cost_are_labeled(dataset, tmp_path):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / "results", samples, count=len(samples))
    build_page(manifest, tmp_path / "results", tmp_path / "site", config)
    html = (tmp_path / "site/index.html").read_text()
    assert "Measurements complete" in html
    assert "estimated run cost" in html


def test_paused_run_reason_is_visible(dataset, tmp_path):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / "results", samples)
    path = tmp_path / "results/summary.json"
    summary = json.loads(path.read_text())
    summary["models"]["test-model"].update(status="paused", reason="Provider is temporarily unavailable")
    path.write_text(json.dumps(summary))
    build_page(manifest, tmp_path / "results", tmp_path / "site", config)
    html = (tmp_path / "site/index.html").read_text()
    assert "Paused" in html
    assert "Provider is temporarily unavailable" in html


def test_montages_cover_every_axis_and_embed_exact_source_bytes(dataset, tmp_path):
    manifest, samples, config = dataset
    output = tmp_path / "site"
    report = build_page(manifest, tmp_path / "results", output, config)
    by_id = {sample["taskId"]: sample for sample in samples}
    axes = {"category": "category", "weight": "weight", "modifier": "modifier", "kerning": "kerning", "line_height": "lineHeight", "font_family": "fontName"}
    for section in report["sections"]:
        if section["id"] not in axes:
            continue
        axis = axes[section["id"]]
        selected = [by_id[task_id] for task_id in section["sample_ids"]]
        assert {sample[axis] for sample in selected} == {sample[axis] for sample in samples}
        svg = ET.parse(output / section["asset"])
        for group in svg.findall("{http://www.w3.org/2000/svg}g"):
            image = group.find("{http://www.w3.org/2000/svg}image")
            assert image is not None
            sample = by_id[group.attrib["data-task-id"]]
            assert base64.b64decode(image.attrib["href"].split(",", 1)[1]) == Path(sample["imagePath"]).read_bytes()


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h3_count = 0
        self.script_sources = []

    def handle_starttag(self, tag, attrs):
        if tag == "h3":
            self.h3_count += 1
        if tag == "script" and dict(attrs).get("src"):
            self.script_sources.append(dict(attrs)["src"])


def test_page_is_local_and_untrusted_labels_cannot_escape_data_script(dataset, tmp_path):
    manifest, samples, config = dataset
    data = json.loads(config.read_text())
    data["models"][0]["display_name"] = "</script><script>alert('injection')</script>"
    config.write_text(json.dumps(data))
    output = tmp_path / "site"
    build_page(manifest, tmp_path / "results", output, config)
    html = (output / "index.html").read_text()
    tags = Tags()
    tags.feed(html)
    assert tags.h3_count >= 6
    assert not tags.script_sources
    assert "</script><script>alert('injection')</script>" not in html


def test_build_is_deterministic(dataset, tmp_path):
    manifest, samples, config = dataset
    first, second = tmp_path / "one", tmp_path / "two"
    build_page(manifest, tmp_path / "results", first, config)
    build_page(manifest, tmp_path / "results", second, config)
    assert {p.relative_to(first): p.read_bytes() for p in first.rglob("*") if p.is_file()} == {
        p.relative_to(second): p.read_bytes() for p in second.rglob("*") if p.is_file()
    }

@pytest.mark.parametrize('tasks', [None, [None], [{'task_id': []}]])
def test_malformed_task_rows_are_excluded_without_breaking_page(dataset, tmp_path, tasks):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / 'results', samples)
    path = tmp_path / 'results/scorecard_test-model.json'
    card = json.loads(path.read_text())
    card['tasks'] = tasks
    path.write_text(json.dumps(card))
    report = build_page(manifest, tmp_path / 'results', tmp_path / 'site', config)
    assert report['models'][0]['completed'] == 0
    assert report['warnings']


def test_corrupt_scorecard_json_is_excluded_with_warning(dataset, tmp_path):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / 'results', samples)
    (tmp_path / 'results/scorecard_test-model.json').write_text('{unfinished')
    report = build_page(manifest, tmp_path / 'results', tmp_path / 'site', config)
    assert report['models'][0]['completed'] == 0
    assert report['warnings']


def test_partial_comparison_records_intersection_of_measured_inputs(dataset, tmp_path):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / 'results', samples, count=2)
    settings = json.loads(config.read_text())
    settings['models'].append({**settings['models'][0], 'id': 'second', 'display_name': 'Second'})
    config.write_text(json.dumps(settings))
    card = json.loads((tmp_path / 'results/scorecard_test-model.json').read_text())
    card.update(model_id='second', tasks=card['tasks'][1:], total_tasks=1)
    card['cohort_fingerprint'] = hashlib.sha256(json.dumps(['task-1']).encode()).hexdigest()
    (tmp_path / 'results/scorecard_second.json').write_text(json.dumps(card))
    report = build_page(manifest, tmp_path / 'results', tmp_path / 'site', config)
    assert report['comparison']['task_ids'] == ['task-1']
    assert report['comparison']['count'] == 1
    assert report['comparison']['models']['test-model']['composite'] == 1.0
    assert report['comparison']['models']['second']['composite'] == 1.0
    assert 'Shared comparison: 1 input' in (tmp_path / 'site/index.html').read_text()


def test_invalid_dataset_gate_prevents_valid_benchmark_claims(dataset, tmp_path, monkeypatch):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / "results", samples, count=len(samples))
    monkeypatch.setattr("baseline.build_page.validate_dataset", lambda path: {"valid": False, "errors": ["Font provenance missing"]})
    report = build_page(manifest, tmp_path / "results", tmp_path / "site", config)
    assert not report["validity"]["valid"]
    assert report["models"][0]["completed"] == 0
    html = (tmp_path / "site/index.html").read_text()
    assert "Dataset validity checks failed" in html
    assert "validated inputs" not in html


@pytest.mark.parametrize("field", ["evaluation_protocol_fingerprint", "cohort_fingerprint", "grading_version"])
def test_page_excludes_incompatible_protocol_or_cohort(dataset, tmp_path, field):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / "results", samples)
    path = tmp_path / "results/scorecard_test-model.json"
    card = json.loads(path.read_text())
    card[field] = "historical"
    path.write_text(json.dumps(card))
    report = build_page(manifest, tmp_path / "results", tmp_path / "site", config)
    assert report["models"][0]["completed"] == 0
    assert report["warnings"]

@pytest.mark.parametrize(("field", "value"), [("status", []), ("error_kind", {}), ("category_correct", "true")])
def test_malformed_status_and_grading_fields_are_excluded(dataset, tmp_path, field, value):
    manifest, samples, config = dataset
    write_scorecard(tmp_path / "results", samples)
    path = tmp_path / "results/scorecard_test-model.json"
    card = json.loads(path.read_text())
    if field == "status":
        card[field] = value
    else:
        card["tasks"][0][field] = value
    path.write_text(json.dumps(card))
    report = build_page(manifest, tmp_path / "results", tmp_path / "site", config)
    assert report["models"][0]["completed"] == 0
    assert report["warnings"]
