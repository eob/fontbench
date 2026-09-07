"""Tests for FontBench dataset integrity and baseline grading logic."""

import json
import os
from pathlib import Path
import pytest
import tomlkit

from baseline.evaluator import BaselineEvaluator, grade_prediction, normalize_font_name


def test_normalize_font_name():
    assert normalize_font_name("Arial") == "arial"
    assert normalize_font_name("Times New Roman") == "timesnewroman"
    assert normalize_font_name("  Comic Sans MS!  ") == "comicsansms"
    assert normalize_font_name("") == ""


def test_grade_prediction_matches_canonical():
    assert grade_prediction("Arial", "Arial", ["arial mt"]) is True
    assert grade_prediction("arial", "Arial", ["arial mt"]) is True
    assert grade_prediction("This is set in Arial.", "Arial", ["arial mt"]) is True


def test_grade_prediction_matches_alias():
    assert grade_prediction("Times", "Times New Roman", ["times new roman", "times"]) is True
    assert grade_prediction("Helvetica Neue", "Helvetica", ["helvetica neue"]) is True


def test_grade_prediction_fails_on_unrelated():
    assert grade_prediction("Roboto", "Arial", ["arial mt"]) is False
    assert grade_prediction("", "Arial", ["arial mt"]) is False
    assert grade_prediction("Times New Roman", "Comic Sans MS", ["comic sans"]) is False


def test_harbor_dataset_integrity():
    dataset_dir = Path("dataset/fontbench-1")
    assert (dataset_dir / "dataset.toml").exists()

    with open(dataset_dir / "dataset.toml", "r", encoding="utf-8") as f:
        doc = tomlkit.parse(f.read())
        assert doc["dataset"]["name"] == "fontbench-1"
        assert doc["dataset"]["task_dir"] == "tasks"

    tasks_dir = dataset_dir / "tasks"
    assert tasks_dir.exists()
    tasks = list(tasks_dir.iterdir())
    assert len(tasks) == 30, f"Expected 30 tasks, found {len(tasks)}"

    for t in tasks:
        assert (t / "task.toml").exists(), f"Missing task.toml in {t.name}"
        assert (t / "instruction.md").exists(), f"Missing instruction.md in {t.name}"
        assert (t / "environment" / "sample.png").exists(), f"Missing sample.png in {t.name}"
        assert (t / "solution" / "solve.sh").exists(), f"Missing solve.sh in {t.name}"
        assert (t / "tests" / "test.sh").exists(), f"Missing test.sh in {t.name}"
        assert (t / "tests" / "ground_truth.json").exists(), f"Missing ground_truth.json in {t.name}"


def test_baseline_evaluator_mock():
    evaluator = BaselineEvaluator(model_name="mock-model", mock=True)
    scorecard = evaluator.evaluate_manifest("dataset/rendered/manifest.json", limit=6)
    
    assert scorecard.total_tasks == 6
    assert scorecard.avg_latency_sec >= 0.0
    # First 3 are Arial (fail with mock Helvetica), next 3 are Helvetica (pass)
    assert scorecard.correct_tasks == 3
    assert scorecard.overall_accuracy == 0.5
