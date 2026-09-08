"""Run a model matrix with durable task checkpoints and a shared spending limit."""

from __future__ import annotations

import argparse
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, fields
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import signal
import threading
from typing import Any
import uuid

from baseline.evaluator import (
    DEFAULT_PROMPT, GRADING_VERSION, BaselineEvaluator, TaskEvaluationResult,
    dataset_fingerprint, evaluation_protocol_fingerprint, load_manifest,
)
from baseline.model_config import load_model_config
from baseline.releases import (
    DEFAULT_RELEASE, git_code_identity, load_release, model_config_fingerprint,
    release_manifest_path, validate_release,
)
from baseline.run_state import RunStore


def write_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


@contextmanager
def _run_lock(directory: Path):
    # Keep the file after unlocking: unlinking permits competing processes to
    # lock different inodes for the same run and issue duplicate paid requests.
    with (directory / '.runner.lock').open('a+b') as lock:
        try:
            import fcntl
        except ImportError:
            import msvcrt
            lock.seek(0)
            lock.write(b'\0')
            lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise RuntimeError(f'Benchmark run is already running: {directory}') from error
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError(f'Benchmark run is already running: {directory}') from error
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


def run_benchmark(
    manifest_path: str | Path | None = None,
    config_path: str | Path = 'config/models.json',
    output_dir: str | Path = 'results/runs',
    run_id: str | None = None,
    selected_models: list[str] | None = None,
    budget_usd: float | None = 25.0,
    max_tasks: int | None = None,
    concurrency: int = 3,
    mock: bool = False,
    *,
    release: str | None = None,
) -> dict[str, Any]:
    if manifest_path is not None and release is not None:
        raise ValueError('Choose either --release or an unversioned custom --manifest')
    descriptor = load_release(DEFAULT_RELEASE if release is None else release) if manifest_path is None else None
    if descriptor is not None:
        manifest_path = release_manifest_path(descriptor)
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:12]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', run_id):
        raise ValueError('run_id must be a simple name, without directory separators')
    if budget_usd is not None and (budget_usd < 0 or not math.isfinite(budget_usd)):
        raise ValueError('budget_usd must be finite and non-negative')
    if concurrency < 1 or (max_tasks is not None and max_tasks < 0):
        raise ValueError('concurrency must be positive and max_tasks non-negative')
    models = load_model_config(config_path)
    if selected_models:
        unknown = set(selected_models) - {model['id'] for model in models}
        if unknown:
            raise ValueError(f'Unknown or disabled models: {", ".join(sorted(unknown))}')
        models = [model for model in models if model['id'] in selected_models]
    if not models:
        raise ValueError('No enabled models selected')
    anthropic_workspace_id = None
    if not mock and any(model['provider'] == 'anthropic' for model in models):
        anthropic_workspace_id = os.environ.get('ANTHROPIC_WORKSPACE_ID', '').strip() or None
        if anthropic_workspace_id and not re.fullmatch(r'wrkspc_[A-Za-z0-9]+', anthropic_workspace_id):
            raise ValueError('ANTHROPIC_WORKSPACE_ID must be a wrkspc_ workspace ID')
    if not mock and budget_usd is not None and any(
        model.get(key) is None for model in models for key in ('input_per_m', 'output_per_m')
    ):
        raise ValueError('A spending limit requires recorded pricing for each selected model')

    release_items = validate_release(descriptor, manifest_path) if descriptor else None
    if not mock:
        from baseline.validate_dataset import require_valid_dataset
        require_valid_dataset(manifest_path)
    items = release_items if release_items is not None else load_manifest(str(manifest_path))
    fingerprint = descriptor['dataset_fingerprint'] if descriptor else dataset_fingerprint(items)
    protocol_fingerprint = descriptor['evaluation_protocol_fingerprint'] if descriptor else evaluation_protocol_fingerprint()
    run_fingerprint = hashlib.sha256(f'{fingerprint}:{protocol_fingerprint}'.encode()).hexdigest()
    identity = {
        'schema_version': 1, 'run_id': run_id,
        'benchmark_version': descriptor['benchmark_version'] if descriptor else None,
        'dataset_git_commit': descriptor['dataset_git_commit'] if descriptor else None,
        'dataset_git_path': descriptor['dataset_git_path'] if descriptor else None,
        'dataset_fingerprint': fingerprint, 'evaluation_protocol_fingerprint': protocol_fingerprint,
        'grading_version': GRADING_VERSION, 'expected_task_count': len(items), 'mock': mock,
    }
    if descriptor:
        run_fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    code_identity = git_code_identity()
    items.sort(key=lambda item: item['taskId'])
    random.Random(0).shuffle(items)
    selected_items = items[:max_tasks] if max_tasks is not None else items
    directory = Path(output_dir)
    if descriptor:
        directory /= descriptor['benchmark_version']
    directory /= f'mock-{run_id}' if mock else run_id
    directory.mkdir(parents=True, exist_ok=True)
    with _run_lock(directory), ExitStack() as resources:
        state_path = directory / 'state.sqlite3'
        if not state_path.exists() and (
            any((directory / name).exists() for name in ('summary.json', 'run.json', 'attempts.jsonl'))
            or any(directory.glob('scorecard_*.json'))
        ):
            raise ValueError('Existing run artifacts have no checkpoint database. Restore state.sqlite3 or use a new run ID.')
        result_fields = {field.name for field in fields(TaskEvaluationResult)}
        clients = {}
        for model in models:
            client = BaselineEvaluator(
                model_name=model['model'], provider=model['provider'], mock=mock,
                api_key_env=model.get('api_key_env'), base_url=model.get('base_url'),
                max_output_tokens=model.get('max_output_tokens', 1024),
            )
            resources.callback(client.close)
            if model['provider'] == 'anthropic' and anthropic_workspace_id:
                # Configure account routing outside the frozen inference protocol.
                client._client._http.headers['anthropic-workspace-id'] = anthropic_workspace_id
            clients[model['id']] = client
        model_by_id = {model['id']: model for model in models}
        # Reserve two possible HTTP attempts before scheduling. Unmetered
        # attempts retain this estimate instead of silently becoming free.
        reserve = {
            model['id']: 0.0 if mock else None if model.get('input_per_m') is None or model.get('output_per_m') is None else (
                5000 * model['input_per_m'] + model.get('max_output_tokens', 1024) * model['output_per_m']
            ) / 1_000_000 for model in models
        }

        with RunStore(state_path) as store:
            store.register_run(run_id, run_fingerprint, {**identity, **code_identity,
                                                        'manifest_path': str(Path(manifest_path).resolve())})
            unknown_historical_costs = store.has_unknown_costs(run_id)
            if budget_usd is not None and unknown_historical_costs:
                raise ValueError('Cannot enforce a cumulative spending limit: prior attempts have unknown costs')
            created_at = next(row['created_at'] for row in store.list_runs() if row['run_id'] == run_id)
            metadata_path = directory / 'run.json'
            if metadata_path.exists():
                run_metadata = json.loads(metadata_path.read_text())
                if (not isinstance(run_metadata, dict) or run_metadata.get('created_at') != created_at
                        or any(run_metadata.get(key) != value for key, value in identity.items())):
                    raise ValueError('Run metadata disagrees with the checkpoint/release identity')
                history = run_metadata.get('invocations')
                if (not isinstance(history, list) or not history
                        or any(not isinstance(entry, dict) or not isinstance(entry.get('models'), list)
                               or not entry['models'] or any(not isinstance(model, dict) for model in entry['models'])
                               for entry in history)):
                    raise ValueError('Run metadata has malformed invocation history')
                historical_configs = [model for entry in history for model in entry['models']]
                if any(state['config'] not in historical_configs for state in store.model_states(run_id).values()):
                    raise ValueError('Run invocation history has lost a checkpoint model configuration')
            else:
                if store.model_states(run_id):
                    raise ValueError('Existing checkpoint has lost run metadata. Restore run.json before resuming.')
                run_metadata = {**identity, 'created_at': created_at, 'invocations': []}
            for model in models:
                store.register_model(run_id, model['id'], model)
            invocation = {**code_identity, 'started_at': datetime.now(timezone.utc).isoformat(),
                          'models': models, 'max_tasks': max_tasks, 'concurrency': concurrency,
                          'budget_usd': budget_usd, 'status': 'running'}
            if anthropic_workspace_id:
                invocation['anthropic_workspace_id'] = anthropic_workspace_id
            run_metadata['invocations'].append(invocation)
            # Previously registered models remain in reports even when this
            # invocation selects only new models. Aggregation makes no requests.
            reported_models = [state['config'] for state in store.model_states(run_id).values()]
            completed = {model['id']: store.completed_results(run_id, model['id']) for model in reported_models}
            item_by_id = {item['taskId']: item for item in items}
            for model in reported_models:
                for task_id, result in completed[model['id']].items():
                    item = item_by_id.get(task_id)
                    if item is None:
                        raise ValueError(f'Unknown checkpoint task: {task_id}')
                    expected = {
                        'task_id': task_id, 'model_name': model['model'], 'provider': model['provider'],
                        'font_id': item['fontId'], 'target_canonical': item['fontName'],
                        'target_aliases': item.get('aliases', []), 'category': item['category'],
                        'weight': item['weight'], 'modifier': item['modifier'], 'kerning': item['kerning'],
                        'line_height': item['lineHeight'], 'width_id': item['widthId'], 'width_px': item['widthPx'],
                    }
                    if any(result.get(key) != value for key, value in expected.items()):
                        raise ValueError(f'Inconsistent checkpoint identity or targets: {model["id"]}/{task_id}')
            pending = deque((model['id'], item) for item in selected_items for model in models
                            if item['taskId'] not in completed[model['id']])
            blocked_providers: set[str] = set()
            blocked_models: set[str] = set()
            status = 'running'
            scorecards = {}
            attempted_ids = {model['id']: set(store.results(run_id, model['id'])) for model in reported_models}
            last_attempt_sequence = None

            def snapshot(changed_model_id: str | None = None) -> dict:
                nonlocal last_attempt_sequence
                state = store.model_states(run_id)
                updated_at = datetime.now(timezone.utc).isoformat()
                provenance = {**identity, **code_identity, 'created_at': created_at, 'updated_at': updated_at}
                summary = {**provenance, 'budget_usd': budget_usd,
                           'spent_cost_usd': store.spent_cost(run_id), 'cost_incomplete': unknown_historical_costs,
                           'status': status, 'models': {},
                           'interruption_signal': int(interruption_signal) if interrupted else None}
                for model in reported_models:
                    model_id = model['id']
                    saved = completed[model_id]
                    if changed_model_id is None or changed_model_id == model_id:
                        results = [TaskEvaluationResult(**{key: value for key, value in result.items() if key in result_fields})
                                   for result in saved.values()]
                        scorer = clients.get(model_id) or next(iter(clients.values()))
                        scorecard = asdict(scorer.score_results(results, len(items)))
                        scorecard.pop('task_results')
                        scorecard['tasks'] = list(saved.values())
                        scorecard.update(provenance, model_id=model_id, model_config=model,
                                         model_name=model['model'], provider=model['provider'],
                                         max_output_tokens=model.get('max_output_tokens', 1024),
                                         pricing={'input_per_m': model.get('input_per_m'), 'output_per_m': model.get('output_per_m')},
                                         model_config_fingerprint=model_config_fingerprint(model))
                        write_json(directory / f'scorecard_{model_id}.json', scorecard)
                        scorecards[model_id] = scorecard
                    scorecard = scorecards[model_id]
                    current = state.get(model_id, {})
                    cost_unknown = not mock and (model.get('input_per_m') is None or model.get('output_per_m') is None)
                    summary['cost_incomplete'] |= cost_unknown and bool(attempted_ids[model_id])
                    summary['models'][model_id] = {
                        'model_config': model, 'model_config_fingerprint': model_config_fingerprint(model),
                        'provider': model['provider'], 'model': model['model'],
                        'max_output_tokens': model.get('max_output_tokens', 1024),
                        'display_name': model.get('display_name', model_id), 'completed': len(saved),
                        'attempted_tasks': len(attempted_ids[model_id]),
                        'status': 'complete' if len(saved) == len(items) else current.get('status', 'pending'),
                        'reason': current.get('reason'), 'cost_usd': None if cost_unknown else store.spent_cost(run_id, model_id),
                        'composite_score': scorecard['overall_composite_score'],
                    }
                write_json(directory / 'summary.json', summary)
                invocation.update(status=status, updated_at=updated_at)
                if status != 'running':
                    invocation['finished_at'] = updated_at
                write_json(metadata_path, run_metadata)
                attempts_path = directory / 'attempts.jsonl'
                attempts = store.attempts(run_id, after_sequence=last_attempt_sequence or 0)
                # Rebuild on resume to repair any interrupted append from the durable checkpoint.
                export_path = attempts_path.with_suffix('.jsonl.tmp') if last_attempt_sequence is None else attempts_path
                with export_path.open('w' if last_attempt_sequence is None else 'a') as output:
                    output.writelines(json.dumps(attempt, ensure_ascii=False) + '\n' for attempt in attempts)
                if last_attempt_sequence is None:
                    export_path.replace(attempts_path)
                last_attempt_sequence = attempts[-1]['sequence'] if attempts else last_attempt_sequence or 0
                return summary

            interrupted = False
            interruption_signal = signal.SIGINT
            fatal_error: Exception | None = None

            def request_stop(signum, frame):
                nonlocal interrupted, interruption_signal
                interrupted = True
                interruption_signal = signum

            if threading.current_thread() is threading.main_thread():
                for stop_signal in (signal.SIGINT, signal.SIGTERM):
                    previous_handler = signal.signal(stop_signal, request_stop)
                    resources.callback(signal.signal, stop_signal, previous_handler)

            snapshot()
            running = {}
            reserved_cost = 0.0

            def checkpoint(future):
                nonlocal reserved_cost, fatal_error, status
                model_id, task_id, request_reserve = running.pop(future)
                reserved_cost -= request_reserve
                model = model_by_id[model_id]
                worker_failed = False
                try:
                    result = asdict(future.result())
                except Exception as error:
                    worker_failed = True
                    fatal_error = fatal_error or error
                    status = 'failed'
                    pending.clear()
                    # An unexpected worker failure can happen after a request was
                    # paid. Retain a retryable error and the full reserved cost.
                    result = {'task_id': task_id, 'model_name': model['model'], 'provider': model['provider'],
                              'error': f'{type(error).__name__}: {error}', 'error_kind': 'other',
                              'request_attempts': None, 'unmetered_attempts': None}
                if mock:
                    result['cost_usd'] = 0.0
                elif reserve[model_id] is None:
                    result['cost_usd'] = None
                elif worker_failed:
                    result['cost_usd'] = request_reserve
                else:
                    metered = ((result.get('input_tokens') or 0) * model['input_per_m']
                               + (result.get('output_tokens') or 0) * model['output_per_m']) / 1_000_000
                    result['cost_usd'] = metered + reserve[model_id] * result.get('unmetered_attempts', 0)
                result['cost_estimated'] = worker_failed or bool(result.get('unmetered_attempts', 0))
                result['recorded_at'] = datetime.now(timezone.utc).isoformat()
                store.save_result(run_id, model_id, task_id, result)
                failure = result.get('error_kind')
                attempted_ids[model_id].add(task_id)
                if not result.get('error') or failure == 'invalid_response':
                    completed[model_id][task_id] = result
                if failure in {'credits', 'authentication', 'rate_limit'}:
                    blocked_providers.add(model['provider'])
                    for sibling in models:
                        if sibling['provider'] == model['provider']:
                            store.save_model_state(run_id, sibling['id'], 'paused', result.get('error'))
                elif result.get('error') and failure != 'invalid_response':
                    blocked_models.add(model_id)
                    store.save_model_state(run_id, model_id, 'paused', result.get('error'))
                print(f"{model_id} / {task_id}: {failure or 'saved'} | estimated spend ${store.spent_cost(run_id):.4f}", flush=True)
                snapshot(model_id)

            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                while pending or running:
                    try:
                        if interrupted or fatal_error:
                            pending.clear()
                        while pending and len(running) < concurrency and not interrupted:
                            model_id, item = pending.popleft()
                            model = model_by_id[model_id]
                            if model_id in blocked_models or model['provider'] in blocked_providers:
                                continue
                            request_reserve = 2 * (reserve[model_id] or 0.0)
                            if budget_usd is not None and store.spent_cost(run_id) + request_reserve > budget_usd + 1e-9:
                                status = 'budget_exhausted'
                                blocked_models.add(model_id)
                                store.save_model_state(run_id, model_id, 'budget_exhausted', 'Increase --budget-usd to resume')
                                continue
                            if budget_usd is not None and store.spent_cost(run_id) + reserved_cost + request_reserve > budget_usd + 1e-9:
                                pending.appendleft((model_id, item))
                                break
                            store.save_model_state(run_id, model_id, 'running')
                            future = pool.submit(clients[model_id]._eval_single_task, item, DEFAULT_PROMPT)
                            running[future] = (model_id, item['taskId'], request_reserve)
                            reserved_cost += request_reserve
                        if not running:
                            break
                        done, _ = wait(running, return_when=FIRST_COMPLETED)
                        for future in done:
                            checkpoint(future)
                    except KeyboardInterrupt:
                        interrupted = True
                    except Exception as error:
                        fatal_error = fatal_error or error
                        status = 'failed'
                        pending.clear()

            if fatal_error:
                status = 'failed'
            elif interrupted:
                status = 'interrupted'
            elif all(len(saved) == len(items) for saved in completed.values()):
                status = 'complete'
            elif status != 'budget_exhausted':
                status = 'paused' if blocked_providers or blocked_models else 'partial'
            for model in models:
                model_id = model['id']
                if len(completed[model_id]) == len(items):
                    store.save_model_state(run_id, model_id, 'complete')
                elif model_id not in blocked_models and model['provider'] not in blocked_providers:
                    reason = str(fatal_error) if fatal_error else 'Interrupted; resume to continue' if interrupted else None
                    store.save_model_state(run_id, model_id, 'paused' if fatal_error or interrupted else 'partial', reason)
            summary = snapshot()
            if fatal_error:
                raise fatal_error
            return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--release', help=f'Frozen benchmark version (default: {DEFAULT_RELEASE})')
    source.add_argument('--manifest', help='Custom manifest; outputs are explicitly unversioned')
    parser.add_argument('--config', default='config/models.json')
    parser.add_argument('--output-dir', default='results/runs')
    parser.add_argument('--run-id', help='Stable ID to resume; omitted creates a new unique run')
    parser.add_argument('--models', nargs='+')
    parser.add_argument('--budget-usd', type=float, default=25.0, help='Total cumulative estimated USD limit for this run')
    parser.add_argument('--no-budget-limit', action='store_true')
    parser.add_argument('--max-tasks', type=int, help='Evaluate a reproducible subset per model; resume without this flag to extend it')
    parser.add_argument('--concurrency', type=int, default=3)
    parser.add_argument('--mock', action='store_true')
    args = parser.parse_args()
    summary = run_benchmark(args.manifest, args.config, args.output_dir, args.run_id, args.models,
                            None if args.no_budget_limit else args.budget_usd, args.max_tasks, args.concurrency, args.mock,
                            release=args.release)
    print(json.dumps(summary, indent=2))
    if summary['status'] == 'interrupted':
        raise SystemExit(128 + summary['interruption_signal'])


if __name__ == '__main__':
    main()
