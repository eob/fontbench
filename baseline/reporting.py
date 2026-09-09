"""Shared scorecard integrity checks for report consumers."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
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
    if card.get("status") not in ("complete", "partial") or (
            card["status"] == "complete" and len(tasks) != card["expected_task_count"]):
        raise ValueError("Inconsistent completion status")
    if complete and (card["status"] != "complete" or not tasks or card["mock"]):
        raise ValueError("Only complete live runs are eligible")
    for task in tasks:
        if any(not isinstance(task.get(f"{key}_correct"), bool) for key in DIMENSIONS):
            raise ValueError("Invalid grading flags")
        if (task.get("error_kind") not in (None, "invalid_response")
                or task.get("error") and task.get("error_kind") != "invalid_response"):
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


def _ledger_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Missing ledger timestamp")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Malformed ledger timestamp") from error
    if timestamp.tzinfo is None:
        raise ValueError("Ledger timestamps must specify a timezone")
    return timestamp.astimezone(timezone.utc)


def _code_identity(record: dict) -> tuple[str | None, bool | None]:
    if "runner_git_commit" not in record or "runner_git_dirty" not in record:
        raise ValueError("Missing runner Git provenance")
    commit, dirty = record["runner_git_commit"], record["runner_git_dirty"]
    if commit is None and dirty is None:
        return None, None
    if (not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit)
            or not isinstance(dirty, bool)):
        raise ValueError("Invalid runner Git provenance")
    return commit, dirty


def aggregate_release_runs(release: dict, items: list[dict], results_root: str | Path, *, root: str | Path | None = None) -> dict:
    """Keep the first recorded final answer per release, inference setup, and task."""
    from baseline.model_config import _ModelConfig
    from baseline.releases import model_config_fingerprint

    results_directory = Path(results_root)
    version_root = results_directory / release["benchmark_version"]
    by_id = {item["taskId"]: item for item in items}
    warnings, excluded, runs = [], [], []
    candidates = []
    origins_by_config = {}
    identity = {key: release[key] for key in (
        "schema_version", "benchmark_version", "dataset_git_commit", "dataset_git_path",
        "dataset_fingerprint", "evaluation_protocol_fingerprint", "expected_task_count",
    )}
    for directory in sorted(results_directory.iterdir()) if results_directory.exists() else []:
        if directory != version_root and directory.is_dir() and (
                (directory / "summary.json").exists() or any(directory.glob("scorecard_*.json"))):
            excluded.append({"path": directory.name, "reason": "Unversioned or historical run"})
    for directory in sorted(version_root.iterdir()) if version_root.exists() else []:
        if not directory.is_dir():
            continue
        run_path = f'{release["benchmark_version"]}/{directory.name}'
        if any((directory / name).exists() for name in ('finalization.json', 'final_results.json')):
            from baseline.finalize import verify_finalization
            try:
                verify_finalization(directory, root=root)
            except (ValueError, RuntimeError, OSError) as error:
                reason = f'Sealed run verification failed: {error}'
                warnings.append(f'Excluded {run_path}: {reason}')
                excluded.append({'path': run_path, 'reason': reason})
                continue
        summary = read_report_json(directory / "summary.json", warnings)
        metadata = read_report_json(directory / "run.json", warnings)
        try:
            if (not summary or any(summary.get(key) != value for key, value in identity.items())
                    or summary.get("mock") is not False or summary.get("run_id") != directory.name
                    or not isinstance(summary.get("models"), dict)):
                raise ValueError("Incompatible release, dataset, protocol, run ID, or mock provenance")
            created, updated = _ledger_time(summary.get("created_at")), _ledger_time(summary.get("updated_at"))
            if updated < created:
                raise ValueError("Run update precedes its creation")
            if (not metadata or any(metadata.get(key) != value for key, value in identity.items())
                    or metadata.get("mock") is not False or metadata.get("run_id") != directory.name
                    or _ledger_time(metadata.get("created_at")) != created):
                raise ValueError("Run metadata disagrees with the release or summary")
            invocations = metadata.get("invocations")
            if not isinstance(invocations, list) or not invocations or any(not isinstance(row, dict) for row in invocations):
                raise ValueError("Missing run invocation history")
            code_identities = {_code_identity(invocation) for invocation in invocations}
            if _code_identity(summary) != _code_identity(invocations[-1]):
                raise ValueError("Summary runner provenance disagrees with its latest invocation")
            for invocation in invocations:
                started, last_update = _ledger_time(invocation.get("started_at")), _ledger_time(invocation.get("updated_at"))
                if (not created <= started <= last_update <= updated
                        or not isinstance(invocation.get("models"), list) or not invocation["models"]
                        or any(not isinstance(model, dict) for model in invocation["models"])):
                    raise ValueError("Invalid invocation chronology or model configurations")
                if "finished_at" in invocation and not started <= _ledger_time(invocation["finished_at"]) <= updated:
                    raise ValueError("Invalid invocation finish time")
        except ValueError as error:
            warnings.append(f"Excluded {run_path}: {error}")
            excluded.append({"path": run_path, "reason": str(error)})
            continue
        run = {"run_id": directory.name, "path": run_path,
               "created_at": created.isoformat().replace("+00:00", "Z"),
               "updated_at": updated.isoformat().replace("+00:00", "Z"),
               "runner_git_commit": summary.get("runner_git_commit"),
               "runner_git_dirty": summary.get("runner_git_dirty"),
               "spent_cost_usd": summary.get("spent_cost_usd"),
               "cost_incomplete": summary.get("cost_incomplete", True),
               "has_attempt_ledger": (directory / "attempts.jsonl").is_file(),
               "attempt_history_status": "available" if (directory / "attempts.jsonl").is_file() else "missing",
               "invocations": invocations}
        runs.append(run)
        for card_path in sorted(directory.glob("scorecard_*.json")):
            card = read_report_json(card_path, warnings)
            try:
                tasks = scorecard_tasks(card)
                if (any(card.get(key) != value for key, value in identity.items())
                        or card.get("mock") is not False or card.get("run_id") != directory.name):
                    raise ValueError("Scorecard release/run provenance disagrees with its ledger")
                config = _ModelConfig.model_validate_json(json.dumps(card.get("model_config"))).model_dump(mode="json")
                config_hash = model_config_fingerprint(config)
                state = summary["models"].get(config["id"])
                if (card.get("model_config_fingerprint") != config_hash
                        or card.get("model_id") != config["id"]
                        or card_path.name != f'scorecard_{config["id"]}.json'
                        or card.get("model_name") != config["model"] or card.get("provider") != config["provider"]
                        or card.get("max_output_tokens") != config["max_output_tokens"]
                        or not isinstance(state, dict) or state.get("model_config") != card["model_config"]
                        or state.get("model_config_fingerprint") != config_hash
                        or type(state.get("completed")) is not int or state["completed"] != len(tasks)
                        or _code_identity(card) not in code_identities
                        or not any(card["model_config"] in invocation["models"] for invocation in invocations)):
                    raise ValueError("Inconsistent recorded model configuration")
                card_updated = _ledger_time(card.get("updated_at"))
                if _ledger_time(card.get("created_at")) != created or not created <= card_updated <= updated:
                    raise ValueError("Scorecard chronology disagrees with its ledger")
                timed_tasks = []
                for task in tasks:
                    item = by_id.get(task["task_id"])
                    if item is None:
                        raise ValueError("Unknown release task")
                    targets = {"font_id": item["fontId"], "target_canonical": item["fontName"],
                               "target_aliases": item.get("aliases", []), "category": item["category"],
                               "weight": item["weight"], "modifier": item["modifier"], "kerning": item["kerning"],
                               "line_height": item["lineHeight"], "width_id": item["widthId"], "width_px": item["widthPx"],
                               "model_name": config["model"], "provider": config["provider"]}
                    if any(task.get(key) != value for key, value in targets.items()):
                        raise ValueError("Task targets or model identity disagree with the frozen release")
                    recorded = _ledger_time(task.get("recorded_at"))
                    if not created <= recorded <= card_updated:
                        raise ValueError("Task recording falls outside its ledger chronology")
                    if not any(_ledger_time(invocation["started_at"]) <= recorded <= _ledger_time(invocation["updated_at"])
                               for invocation in invocations if card["model_config"] in invocation["models"]):
                        raise ValueError("Task recording falls outside an invocation of its model configuration")
                    timed_tasks.append((recorded, task))
            except (ValueError, TypeError) as error:
                path = f"{run_path}/{card_path.name}"
                warnings.append(f"Excluded {path}: {error}")
                excluded.append({"path": path, "reason": str(error)})
                continue
            origin = {**run, "model_id": config["id"], "model_config": config,
                      "task_count": len(tasks), "accepted_task_count": 0, "duplicate_count": 0,
                      "attempted_tasks": state.get("attempted_tasks"),
                      "cost_usd": state.get("cost_usd") if finite_nonnegative(state.get("cost_usd")) else None,
                      "scorecard": card_path.name}
            origins_by_config.setdefault(config_hash, []).append(origin)
            candidates.extend((recorded, directory.name, config["id"], config_hash, task, origin)
                              for recorded, task in timed_tasks)
    selected = {config_hash: {} for config_hash in origins_by_config}
    for recorded, run_id, _, config_hash, task, origin in sorted(candidates, key=lambda entry: entry[:3]):
        if task["task_id"] in selected[config_hash]:
            origin["duplicate_count"] += 1
        else:
            selected[config_hash][task["task_id"]] = {
                **task, "source_run_id": run_id, "recorded_at": recorded.isoformat().replace("+00:00", "Z"),
            }
            origin["accepted_task_count"] += 1
    models, tasks_by_model = [], {}
    for config_hash, origins in sorted(origins_by_config.items()):
        origins.sort(key=lambda origin: (_ledger_time(origin["created_at"]), origin["run_id"], origin["model_id"]))
        config = origins[0]["model_config"]
        tasks = sorted(selected[config_hash].values(), key=lambda task: task["task_id"])
        tasks_by_model[config_hash] = tasks
        models.append({**config, "id": config_hash, "model_config_fingerprint": config_hash,
                       "completed": len(tasks), "expected": len(items), "metrics": metrics(tasks),
                       "status": "complete" if len(tasks) == len(items) else "partial" if tasks else "pending",
                       "run_state": "complete" if len(tasks) == len(items) else "pending", "reason": None,
                       "mock": False, "origins": origins,
                       "duplicate_count": sum(origin["duplicate_count"] for origin in origins),
                       "invalid_response_count": sum(task.get("error_kind") == "invalid_response" for task in tasks),
                       "cohort_fingerprint": hashlib.sha256(json.dumps(sorted(task["task_id"] for task in tasks)).encode()).hexdigest(),
                       "cost_usd": sum(origin["cost_usd"] for origin in origins)
                       if all(origin["cost_usd"] is not None for origin in origins) else None})
    runs.sort(key=lambda run: (_ledger_time(run["created_at"]), run["run_id"]))
    return {"models": models, "tasks_by_model": tasks_by_model, "runs": runs,
            "warnings": warnings, "excluded_runs": excluded,
            "duplicate_policy": "First recorded final answer per inference configuration and task; ties use run ID, then model ID."}
