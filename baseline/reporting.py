"""Shared scorecard integrity checks for report consumers."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from baseline.evaluator import GRADING_VERSION, evaluation_protocol_fingerprint

DIMENSIONS = ("font", "category", "weight", "modifier", "kerning", "line_height")


def read_report_json(path: Path, warnings: list[str]) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError("Expected an object")
        return value
    except (OSError, ValueError) as error:
        warnings.append(f"Excluded malformed {path.name}: {error}")
        return {}


def scorecard_tasks(card: dict, *, complete: bool = False) -> list[dict]:
    """Reject incomplete provenance and malformed rows before computing metrics."""
    tasks = card.get("tasks")
    if not isinstance(tasks, list) or any(not isinstance(task, dict) for task in tasks):
        raise ValueError("Malformed task rows")
    ids = [task.get("task_id") for task in tasks]
    if (any(not isinstance(task_id, str) or not task_id for task_id in ids)
            or len(set(ids)) != len(ids)
            or type(card.get("total_tasks")) is not int or card["total_tasks"] != len(tasks)
            or type(card.get("expected_task_count")) is not int
            or card["expected_task_count"] <= 0 or len(tasks) > card["expected_task_count"]):
        raise ValueError("Inconsistent task coverage")
    if (str(card.get("grading_version")) != GRADING_VERSION
            or card.get("evaluation_protocol_fingerprint") != evaluation_protocol_fingerprint()
            or not isinstance(card.get("dataset_fingerprint"), str) or not card["dataset_fingerprint"]
            or card.get("cohort_fingerprint") != hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest()
            or not isinstance(card.get("mock"), bool)):
        raise ValueError("Incompatible dataset, protocol, or mock provenance")
    if card.get("status") not in {"complete", "partial"} or (
            card["status"] == "complete" and len(tasks) != card["expected_task_count"]):
        raise ValueError("Inconsistent completion status")
    if complete and (card["status"] != "complete" or not tasks or card["mock"]):
        raise ValueError("Only complete live runs are eligible")
    for task in tasks:
        if any(not isinstance(task.get(f"{key}_correct"), bool) for key in DIMENSIONS):
            raise ValueError("Invalid grading flags")
        if task.get("error_kind") not in {None, "invalid_response"}:
            raise ValueError("Infrastructure failures are not completed measurements")
        if task.get("error_kind") == "invalid_response" and any(task[f"{key}_correct"] for key in DIMENSIONS):
            raise ValueError("Invalid model answers must receive zero credit")
    return tasks


def metrics(tasks: list[dict]) -> dict:
    if not tasks:
        return {key: None for key in (*DIMENSIONS, "composite", "exact")}
    values = {key: sum(task[f"{key}_correct"] for task in tasks) / len(tasks) for key in DIMENSIONS}
    values["composite"] = sum(values.values()) / len(DIMENSIONS)
    values["exact"] = sum(all(task[f"{key}_correct"] for key in DIMENSIONS) for task in tasks) / len(tasks)
    return values


def finite_nonnegative(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0
