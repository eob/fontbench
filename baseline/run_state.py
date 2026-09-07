"""SQLite checkpoints for resumable benchmark runs and their known billed costs."""

from __future__ import annotations

import json
import math
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def _json(value: dict) -> str:
    if not isinstance(value, dict):
        raise TypeError("Checkpoint metadata, configuration, and results must be objects")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _is_completed(result: dict) -> bool:
    # Retrying malformed model answers until one parses would bias the score.
    return not result.get("error") or result.get("error_kind") == "invalid_response"


class RunStore:
    """Persist each finished attempt before starting more paid work.

    Successful answers and invalid model responses are final. Infrastructure
    failures remain retryable and their costs stay in the ledger after a retry.
    Checkpointing cannot make a remote API call and a local commit atomic: a crash
    between them may still require retrying the remote request.
    """

    def __init__(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        try:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=FULL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                );
                CREATE TABLE IF NOT EXISTS models (
                    run_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    reason TEXT,
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    PRIMARY KEY (run_id, model_id),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    cost_usd REAL NOT NULL CHECK (cost_usd >= 0),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                    FOREIGN KEY (run_id, model_id) REFERENCES models(run_id, model_id)
                );
                CREATE INDEX IF NOT EXISTS attempts_run_model ON attempts(run_id, model_id);
                CREATE TABLE IF NOT EXISTS results (
                    run_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, model_id, task_id),
                    FOREIGN KEY (run_id, model_id) REFERENCES models(run_id, model_id)
                );
                COMMIT;
            """)
        except BaseException:
            self._connection.close()
            raise

    def __enter__(self) -> RunStore:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @contextmanager
    def _write(self) -> Iterator[None]:
        with self._lock:
            # Acquire the writer lock before checking identity/completion so two
            # connections cannot both replace a task's first successful result.
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield
                self._connection.commit()
            except BaseException:
                self._connection.rollback()
                raise

    def register_run(self, run_id: str, fingerprint: str, metadata: dict) -> None:
        metadata_json = _json(metadata)
        with self._write():
            self._connection.execute(
                "INSERT INTO runs(run_id, fingerprint, metadata_json) VALUES (?, ?, ?) ON CONFLICT(run_id) DO NOTHING",
                (run_id, fingerprint, metadata_json),
            )
            existing = self._connection.execute("SELECT fingerprint FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if existing[0] != fingerprint:
                raise ValueError(f"Run {run_id!r} already exists with a different fingerprint")

    def register_model(self, run_id: str, model_id: str, config: dict) -> None:
        config_json = _json(config)
        with self._write():
            self._connection.execute(
                "INSERT INTO models(run_id, model_id, config_json) VALUES (?, ?, ?) ON CONFLICT(run_id, model_id) DO NOTHING",
                (run_id, model_id, config_json),
            )
            existing = self._connection.execute(
                "SELECT config_json FROM models WHERE run_id = ? AND model_id = ?", (run_id, model_id)
            ).fetchone()
            if existing[0] != config_json:
                raise ValueError(f"Model {model_id!r} in run {run_id!r} already has a different config")

    def save_result(
        self, run_id: str, model_id: str, task_id: str, result: dict, *, attempt_id: str | None = None
    ) -> bool:
        """Commit a new attempt; return False for an already saved attempt/task.

        Supply a stable attempt_id when retrying a checkpoint write. Missing or
        None cost_usd means unknown cost, preserved in JSON and excluded from the
        known-cost total. Each new failed API attempt needs a new attempt_id.
        """
        result_json = _json(result)
        cost = result.get("cost_usd")
        if cost is None:
            cost = 0.0
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
            raise ValueError("cost_usd must be a finite nonnegative number or None")
        attempt_id = attempt_id or str(uuid.uuid4())
        with self._write():
            existing_attempt = self._connection.execute(
                "SELECT run_id, model_id, task_id, result_json FROM attempts WHERE attempt_id = ?", (attempt_id,)
            ).fetchone()
            if existing_attempt is not None:
                if existing_attempt != (run_id, model_id, task_id, result_json):
                    raise ValueError(f"Attempt {attempt_id!r} already identifies a different attempt result")
                return False
            existing = self._connection.execute(
                "SELECT result_json FROM results WHERE run_id = ? AND model_id = ? AND task_id = ?",
                (run_id, model_id, task_id),
            ).fetchone()
            if existing is not None and _is_completed(json.loads(existing[0])):
                return False
            self._connection.execute(
                "INSERT INTO attempts(attempt_id, run_id, model_id, task_id, result_json, cost_usd) VALUES (?, ?, ?, ?, ?, ?)",
                (attempt_id, run_id, model_id, task_id, result_json, cost),
            )
            self._connection.execute(
                """INSERT INTO results(run_id, model_id, task_id, result_json) VALUES (?, ?, ?, ?)
                   ON CONFLICT(run_id, model_id, task_id) DO UPDATE SET result_json = excluded.result_json""",
                (run_id, model_id, task_id, result_json),
            )
        return True

    def results(self, run_id: str, model_id: str) -> dict[str, dict]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT task_id, result_json FROM results WHERE run_id = ? AND model_id = ? ORDER BY task_id",
                (run_id, model_id),
            ).fetchall()
        return {task_id: json.loads(result_json) for task_id, result_json in rows}

    def completed_results(self, run_id: str, model_id: str) -> dict[str, dict]:
        return {task_id: result for task_id, result in self.results(run_id, model_id).items() if _is_completed(result)}

    def has_unknown_costs(self, run_id: str) -> bool:
        """Check every attempt, including failed attempts superseded by retries."""
        with self._lock:
            rows = self._connection.execute(
                "SELECT result_json FROM attempts WHERE run_id = ?", (run_id,)
            ).fetchall()
        return any(json.loads(result_json).get("cost_usd") is None for (result_json,) in rows)

    def spent_cost(self, run_id: str, model_id: str | None = None) -> float:
        query = "SELECT COALESCE(SUM(cost_usd), 0) FROM attempts WHERE run_id = ?"
        parameters = (run_id,)
        if model_id is not None:
            query += " AND model_id = ?"
            parameters += (model_id,)
        with self._lock:
            return float(self._connection.execute(query, parameters).fetchone()[0])

    def save_model_state(self, run_id: str, model_id: str, status: str, reason: str | None = None) -> None:
        with self._write():
            cursor = self._connection.execute(
                """UPDATE models SET status = ?, reason = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                   WHERE run_id = ? AND model_id = ?""",
                (status, reason, run_id, model_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Model {model_id!r} is not registered in run {run_id!r}")

    def model_states(self, run_id: str) -> dict[str, dict]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT model_id, status, reason, config_json, updated_at FROM models WHERE run_id = ? ORDER BY model_id",
                (run_id,),
            ).fetchall()
        return {
            model_id: {"status": status, "reason": reason, "config": json.loads(config), "updated_at": updated_at}
            for model_id, status, reason, config, updated_at in rows
        }

    def list_runs(self) -> list[dict]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT run_id, fingerprint, metadata_json, created_at FROM runs ORDER BY created_at, run_id"
            ).fetchall()
        return [
            {"run_id": run_id, "fingerprint": fingerprint, "metadata": json.loads(metadata), "created_at": created_at}
            for run_id, fingerprint, metadata, created_at in rows
        ]
