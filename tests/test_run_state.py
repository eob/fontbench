"""Durable run checkpoints and billing history, with no provider calls."""

import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from baseline.run_state import RunStore


def register(store, run_id="run", model_id="vendor/model"):
    store.register_run(run_id, "dataset-sha256", {"dataset": "fixture"})
    store.register_model(run_id, model_id, {"provider": "fixture", "model": "model", "temperature": 0})


def test_reopen_retains_success_usage_and_model_state(tmp_path):
    database = tmp_path / "nested" / "runs.sqlite3"
    result = {"task_id": "task", "error": None, "prediction": "é", "usage": {"input_tokens": 100}, "cost_usd": 0.125}
    with RunStore(database) as store:
        register(store)
        store.save_result("run", "vendor/model", "task", result)
        store.save_model_state("run", "vendor/model", "paused", "credits exhausted")
    with RunStore(database) as store:
        assert store.completed_results("run", "vendor/model") == {"task": result}
        assert store.model_states("run")["vendor/model"]["status"] == "paused"
        assert store.model_states("run")["vendor/model"]["reason"] == "credits exhausted"
        assert store.spent_cost("run") == pytest.approx(0.125)
        assert store.list_runs()[0]["metadata"] == {"dataset": "fixture"}


def test_run_identity_is_immutable_and_registration_is_idempotent(tmp_path):
    with RunStore(tmp_path / "runs.sqlite3") as store:
        register(store)
        store.register_run("run", "dataset-sha256", {"dataset": "new presentation"})
        with pytest.raises(ValueError, match="fingerprint"):
            store.register_run("run", "different-dataset", {})
        assert store.list_runs()[0]["fingerprint"] == "dataset-sha256"
        assert store.list_runs()[0]["metadata"] == {"dataset": "fixture"}
        assert len(store.list_runs()) == 1


def test_model_config_is_canonical_and_immutable(tmp_path):
    with RunStore(tmp_path / "runs.sqlite3") as store:
        register(store)
        store.register_model("run", "vendor/model", {"temperature": 0, "model": "model", "provider": "fixture"})
        with pytest.raises(ValueError, match="config"):
            store.register_model("run", "vendor/model", {"provider": "different"})
        store.save_result("run", "vendor/model", "task", {"error": None})
        assert "task" in store.completed_results("run", "vendor/model")


def test_errors_retry_without_losing_the_cost_of_earlier_attempts(tmp_path):
    with RunStore(tmp_path / "runs.sqlite3") as store:
        register(store)
        error = {"error": "quota", "cost_usd": 0.01}
        store.save_result("run", "vendor/model", "task", error, attempt_id="attempt-1")
        assert store.completed_results("run", "vendor/model") == {}
        assert store.results("run", "vendor/model") == {"task": error}
        success = {"error": None, "cost_usd": 0.02}
        store.save_result("run", "vendor/model", "task", success, attempt_id="attempt-2")
        assert store.completed_results("run", "vendor/model") == {"task": success}
        assert store.spent_cost("run", "vendor/model") == pytest.approx(0.03)


def test_success_is_not_overwritten_or_billed_twice(tmp_path):
    with RunStore(tmp_path / "runs.sqlite3") as store:
        register(store)
        success = {"error": None, "cost_usd": 0.1, "prediction": "first"}
        store.save_result("run", "vendor/model", "task", success)
        store.save_result("run", "vendor/model", "task", {"error": "later error", "cost_usd": 0.2})
        store.save_result("run", "vendor/model", "task", {"error": None, "cost_usd": 0.3})
        assert store.results("run", "vendor/model") == {"task": success}
        assert store.spent_cost("run") == pytest.approx(0.1)


def test_invalid_model_response_is_a_final_result_including_its_error(tmp_path):
    with RunStore(tmp_path / "runs.sqlite3") as store:
        register(store)
        result = {"error": "JSON schema refused", "error_kind": "invalid_response", "raw_prediction": "Arial", "cost_usd": 0.1}
        store.save_result("run", "vendor/model", "task", result)
        assert store.completed_results("run", "vendor/model") == {"task": result}
        store.save_result("run", "vendor/model", "task", {"error": None, "cost_usd": 0.2})
        assert store.results("run", "vendor/model") == {"task": result}
        assert store.spent_cost("run") == pytest.approx(0.1)


def test_error_write_retry_is_idempotent_by_attempt_id(tmp_path):
    with RunStore(tmp_path / "runs.sqlite3") as store:
        register(store)
        error = {"error": "timeout", "cost_usd": 0.1}
        store.save_result("run", "vendor/model", "task", error, attempt_id="request-id")
        store.save_result("run", "vendor/model", "task", error, attempt_id="request-id")
        assert store.spent_cost("run") == pytest.approx(0.1)
        with pytest.raises(ValueError, match="attempt"):
            store.save_result("run", "vendor/model", "other-task", error, attempt_id="request-id")
        assert store.results("run", "vendor/model") == {"task": error}


def test_run_and_model_namespaces_are_independent(tmp_path):
    with RunStore(tmp_path / "runs.sqlite3") as store:
        register(store)
        register(store, run_id="other-run")
        register(store, model_id="other-model")
        store.save_result("run", "vendor/model", "task", {"error": None, "cost_usd": 0.1})
        store.save_result("other-run", "vendor/model", "task", {"error": None, "cost_usd": 0.2})
        store.save_result("run", "other-model", "task", {"error": None, "cost_usd": 0.3})
        assert store.spent_cost("run") == pytest.approx(0.4)
        assert store.spent_cost("other-run") == pytest.approx(0.2)
        assert store.spent_cost("run", "other-model") == pytest.approx(0.3)


def test_result_and_attempt_ledger_commit_atomically(tmp_path):
    database = tmp_path / "runs.sqlite3"
    with RunStore(database) as store:
        register(store)
        with sqlite3.connect(database) as connection:
            connection.execute("""CREATE TRIGGER reject_result BEFORE INSERT ON results
                BEGIN SELECT RAISE(ABORT, 'injected write failure'); END""")
        with pytest.raises(sqlite3.IntegrityError, match="injected write failure"):
            store.save_result("run", "vendor/model", "task", {"error": None, "cost_usd": 0.5})
        assert store.results("run", "vendor/model") == {}
        assert store.spent_cost("run") == 0
    with RunStore(database) as store:
        assert store.results("run", "vendor/model") == {}
        assert store.spent_cost("run") == 0


def test_completed_work_survives_process_exit_without_close(tmp_path):
    database = tmp_path / "runs.sqlite3"
    code = """import os, sys
from baseline.run_state import RunStore
store = RunStore(sys.argv[1])
store.register_run('run', 'dataset-sha256', {})
store.register_model('run', 'model', {})
store.save_result('run', 'model', 'task', {'error': None, 'cost_usd': 0.1})
os._exit(0)
"""
    subprocess.run([sys.executable, "-c", code, str(database)], check=True)
    with RunStore(database) as store:
        assert store.completed_results("run", "model") == {"task": {"error": None, "cost_usd": 0.1}}
        assert store.spent_cost("run") == pytest.approx(0.1)


def test_independent_connections_can_checkpoint_concurrently(tmp_path):
    database = tmp_path / "runs.sqlite3"
    with RunStore(database) as store:
        register(store)

    def save(task_id):
        with RunStore(database) as store:
            register(store)
            store.save_result("run", "vendor/model", str(task_id), {"error": None, "cost_usd": 0.01})

    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(save, range(20)))
    with RunStore(database) as store:
        assert len(store.completed_results("run", "vendor/model")) == 20
        assert store.spent_cost("run") == pytest.approx(0.2)


def test_concurrent_duplicate_successes_cannot_overwrite_each_other(tmp_path):
    database = tmp_path / "runs.sqlite3"
    with RunStore(database) as store:
        register(store)

    def save(worker):
        with RunStore(database) as store:
            return store.save_result("run", "vendor/model", "same-task", {"error": None, "worker": worker, "cost_usd": 0.1})

    with ThreadPoolExecutor(max_workers=4) as workers:
        inserted = list(workers.map(save, range(8)))
    assert sum(inserted) == 1
    with RunStore(database) as store:
        assert len(store.completed_results("run", "vendor/model")) == 1
        assert store.spent_cost("run") == pytest.approx(0.1)


@pytest.mark.parametrize("cost", [-1, float("nan"), float("inf"), "unknown"])
def test_invalid_cost_does_not_create_a_checkpoint(tmp_path, cost):
    with RunStore(tmp_path / "runs.sqlite3") as store:
        register(store)
        with pytest.raises((ValueError, TypeError)):
            store.save_result("run", "vendor/model", "task", {"error": None, "cost_usd": cost})
        assert store.results("run", "vendor/model") == {}
        assert store.spent_cost("run") == 0


def test_unknown_cost_and_error_free_results_are_preserved(tmp_path):
    with RunStore(tmp_path / "runs.sqlite3") as store:
        register(store)
        result = {"error": None, "cost_usd": None, "usage": {"provider_field": [1, 2]}}
        store.save_result("run", "vendor/model", "task", result)
        assert store.completed_results("run", "vendor/model") == {"task": result}
        assert store.spent_cost("run") == 0
