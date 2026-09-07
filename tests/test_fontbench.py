"""Dataset integrity and offline evaluation checks."""

import json
from pathlib import Path

import pytest
import tomlkit
from PIL import Image

from baseline.evaluator import BaselineEvaluator, grade_font_prediction, normalize_font_name


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("value", "expected"),
    [("Arial", "arial"), ("Times New Roman", "timesnewroman"),
     ("  Comic Sans MS!  ", "comicsansms"), ("", "")],
)
def test_normalize_font_name(value, expected):
    assert normalize_font_name(value) == expected


def test_grade_font_prediction_matches_canonical_and_aliases():
    assert grade_font_prediction("arial", "Arial", ["arial mt"])
    assert grade_font_prediction("Arial MT", "Arial", ["arial mt"])
    assert grade_font_prediction("Times", "Times New Roman", ["times"])
    assert not grade_font_prediction("Roboto", "Arial", ["arial mt"])
    assert not grade_font_prediction("", "Arial", ["arial mt"])


def test_harbor_dataset_integrity():
    dataset_dir = ROOT / "dataset/fontbench-1"
    doc = tomlkit.parse((dataset_dir / "dataset.toml").read_text())
    assert doc["dataset"]["name"] == "fontbench-1"
    assert doc["dataset"]["task_dir"] == "tasks"

    tasks = sorted(p for p in (dataset_dir / "tasks").iterdir() if p.is_dir())
    assert len(tasks) == doc["metadata"]["total_tasks"]
    assert tasks
    fonts = set()
    for task in tasks:
        for filename in (
            "task.toml", "instruction.md", "environment/Dockerfile", "environment/sample.png",
            "solution/solve.sh", "tests/test.sh", "tests/ground_truth.json",
        ):
            assert (task / filename).is_file(), f"Missing {filename} in {task.name}"
        config = tomlkit.parse((task / "task.toml").read_text())
        truth = json.loads((task / "tests/ground_truth.json").read_text())
        assert config["metadata"]["name"] == truth["taskId"] == task.name
        assert truth["category"] in {"serif", "non-serif", "mono", "handwriting", "other"}
        assert truth["weight"] in {"thin", "regular", "bold", "black"}
        assert truth["modifier"] in {"regular", "italic", "underline", "strikethrough", "small-caps"}
        assert truth["kerning"] in {"tight", "normal", "loose"}
        assert truth["lineHeight"] in {"tight", "normal", "loose"}
        assert truth["widthPx"] == {"narrow": 220, "medium": 320, "wide": 440}[truth["widthId"]]
        with Image.open(task / "environment/sample.png") as image:
            assert image.format == "PNG"
            assert image.width == truth["widthPx"] * 2
            image.verify()
        fonts.add(truth["canonical"])
    assert len(fonts) == 50


def test_baseline_evaluator_mock(tmp_path):
    sample = {
        "taskId": "fixture-arial", "fontId": "arial", "fontName": "Arial", "aliases": [],
        "category": "non-serif", "weight": "regular", "modifier": "regular",
        "kerning": "normal", "lineHeight": "normal", "widthId": "narrow", "widthPx": 220,
        "imageFilename": "sample.png", "prompt": "Identify the six typographic properties.",
    }
    Image.new("RGB", (440, 200), "white").save(tmp_path / "sample.png")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([sample, {**sample, "taskId": "fixture-georgia", "fontId": "georgia", "fontName": "Georgia", "category": "serif"}]))
    scorecard = BaselineEvaluator(model_name="mock-model", mock=True).evaluate_manifest(str(manifest))

    assert scorecard.total_tasks == 2
    assert scorecard.font_accuracy == 0.5
    assert scorecard.category_accuracy == 0.5
    assert scorecard.overall_exact_match == 0.5
    assert scorecard.overall_composite_score == pytest.approx(5 / 6)
    assert scorecard.avg_latency_sec >= 0.0
    assert all(result.error is None for result in scorecard.task_results)
