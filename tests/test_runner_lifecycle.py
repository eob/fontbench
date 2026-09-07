"""Paid-request lifecycle checks using entirely local evaluator substitutes."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import signal
import threading

import pytest
from PIL import Image

from baseline.evaluator import BaselineEvaluator
from baseline.run_state import RunStore
import baseline.runner as runner


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    Image.new('RGB', (4, 4), 'white').save(tmp_path / 'sample.png')
    sample = dict(taskId='one', fontId='arial', fontName='Arial', aliases=[], category='non-serif',
                  weight='regular', modifier='regular', kerning='normal', lineHeight='normal',
                  widthId='narrow', widthPx=220, imageFilename='sample.png', prompt='Identify the typography.')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps([{**sample, 'taskId': name} for name in ('one', 'two', 'three')]))
    config = tmp_path / 'models.json'
    model = dict(id='model-a', provider='google', model='model-a', display_name='A', enabled=True,
                 api_key_env='TEST_KEY', source_url='https://example.com/models', max_output_tokens=1000,
                 input_per_m=1.0, output_per_m=1.0)
    config.write_text(json.dumps(dict(version=1, verified_at='2026-09-07', models=[model])))
    control = {'calls': [], 'closed': []}

    def default_evaluate(client, item, prompt):
        return replace(BaselineEvaluator._eval_single_task(client, item, prompt),
                       input_tokens=100, output_tokens=10, request_attempts=1)

    control['evaluate'] = default_evaluate
    control['result'] = default_evaluate

    class LocalEvaluator(BaselineEvaluator):
        def __init__(self, model_name, provider, **kwargs):
            super().__init__(model_name=model_name, provider=provider, mock=True)

        def _eval_single_task(self, item, prompt):
            control['calls'].append((self.model_name, item['taskId']))
            return control['evaluate'](self, item, prompt)

        def close(self):
            control['closed'].append(self.model_name)
            super().close()

    monkeypatch.setattr(runner, 'BaselineEvaluator', LocalEvaluator)
    args = dict(manifest_path=manifest, config_path=config, output_dir=tmp_path / 'runs',
                run_id='test', mock=False, budget_usd=1.0, concurrency=2)
    return args, control


def test_interrupt_drains_paid_results_and_does_not_start_more_tasks(campaign, monkeypatch):
    args, control = campaign
    real_wait = runner.wait
    interrupted = False

    def interrupt_once(futures, **kwargs):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt
        return real_wait(futures, **kwargs)

    monkeypatch.setattr(runner, 'wait', interrupt_once)
    summary = None
    try:
        summary = runner.run_benchmark(**args)
    except KeyboardInterrupt:
        pass
    with RunStore(args['output_dir'] / 'test' / 'state.sqlite3') as store:
        assert len(store.completed_results('test', 'model-a')) == 2
    assert len(control['calls']) == 2
    assert summary['status'] == 'interrupted'
    assert control['closed'] == ['model-a']


def test_sigterm_drains_paid_results_and_restores_the_previous_handler(campaign, monkeypatch):
    args, control = campaign
    previous_handler = signal.getsignal(signal.SIGTERM)
    real_wait = runner.wait
    stopped = False

    def stop_once(futures, **kwargs):
        nonlocal stopped
        if not stopped:
            stopped = True
            handler = signal.getsignal(signal.SIGTERM)
            assert callable(handler), 'SIGTERM has no graceful handler'
            handler(signal.SIGTERM, None)
        return real_wait(futures, **kwargs)

    monkeypatch.setattr(runner, 'wait', stop_once)
    summary = runner.run_benchmark(**args)
    assert summary['status'] == 'interrupted'
    assert summary['interruption_signal'] == signal.SIGTERM
    assert len(control['calls']) == 2
    with RunStore(args['output_dir'] / 'test' / 'state.sqlite3') as store:
        assert len(store.completed_results('test', 'model-a')) == 2
    assert signal.getsignal(signal.SIGTERM) == previous_handler
    assert control['closed'] == ['model-a']


def test_worker_exception_drains_other_results_and_preserves_cost(campaign, monkeypatch):
    args, control = campaign
    release = threading.Event()

    def evaluate(client, item, prompt):
        if item['taskId'] == 'one':
            raise RuntimeError('injected worker failure')
        assert release.wait(5)
        return control['result'](client, item, prompt)

    control['evaluate'] = evaluate
    real_wait = runner.wait
    first_wait = True

    def failed_future_first(futures, **kwargs):
        nonlocal first_wait
        if first_wait:
            first_wait = False
            future = next(iter(futures))
            assert isinstance(future.exception(timeout=5), RuntimeError)
            release.set()
            return {future}, set(futures) - {future}
        return real_wait(futures, **kwargs)

    monkeypatch.setattr(runner, 'wait', failed_future_first)
    with pytest.raises(RuntimeError, match='injected worker failure'):
        runner.run_benchmark(**args)
    with RunStore(args['output_dir'] / 'test' / 'state.sqlite3') as store:
        assert len(store.completed_results('test', 'model-a')) == 1
        assert len(store.results('test', 'model-a')) == 2
        assert store.spent_cost('test') >= 0.012
    summary = json.loads((args['output_dir'] / 'test' / 'summary.json').read_text())
    assert summary['status'] == 'failed'
    assert len(control['calls']) == 2
    assert control['closed'] == ['model-a']


def test_simultaneous_runners_cannot_repeat_paid_calls(campaign):
    args, control = campaign
    args['max_tasks'] = 1
    entered = threading.Event()
    release = threading.Event()

    def evaluate(client, item, prompt):
        entered.set()
        assert release.wait(3)
        return control['result'](client, item, prompt)

    control['evaluate'] = evaluate
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(runner.run_benchmark, **args)
        assert entered.wait(3)
        try:
            with pytest.raises(RuntimeError, match='already running'):
                runner.run_benchmark(**args)
        finally:
            release.set()
            first.result(timeout=5)
    assert len(control['calls']) == 1


def test_clients_close_after_success_and_fingerprint_refusal(campaign):
    args, control = campaign
    runner.run_benchmark(**args)
    assert control['closed'] == ['model-a']
    Image.new('RGB', (4, 4), 'black').save(args['manifest_path'].parent / 'sample.png')
    with pytest.raises(ValueError, match='fingerprint'):
        runner.run_benchmark(**args)
    assert control['closed'] == ['model-a', 'model-a']


@pytest.mark.parametrize('retained_artifact', ['summary.json', 'scorecard_model-a.json'])
def test_missing_checkpoint_database_cannot_overwrite_retained_run_artifacts(campaign, retained_artifact):
    args, control = campaign
    runner.run_benchmark(**args, max_tasks=1)
    directory = args['output_dir'] / 'test'
    (directory / 'state.sqlite3').unlink()
    for artifact in directory.glob('*.json'):
        if artifact.name != retained_artifact:
            artifact.unlink()
    original = (directory / retained_artifact).read_bytes()
    control['calls'].clear()
    with pytest.raises(ValueError, match='(?i)restore.*state|new.*run'):
        runner.run_benchmark(**args)
    assert control['calls'] == []
    assert (directory / retained_artifact).read_bytes() == original
    assert not (directory / 'state.sqlite3').exists()


def test_unknown_prices_are_not_reported_as_free_calls(campaign):
    args, _ = campaign
    data = json.loads(args['config_path'].read_text())
    data['models'][0].pop('input_per_m')
    data['models'][0].pop('output_per_m')
    args['config_path'].write_text(json.dumps(data))
    args['budget_usd'] = None
    args['max_tasks'] = 1
    summary = runner.run_benchmark(**args)
    with RunStore(args['output_dir'] / 'test' / 'state.sqlite3') as store:
        result = next(iter(store.completed_results('test', 'model-a').values()))
        assert result['cost_usd'] is None
    assert summary['models']['model-a']['cost_usd'] is None
    assert summary['cost_incomplete'] is True
    card = json.loads((args['output_dir'] / 'test' / 'scorecard_model-a.json').read_text())
    assert card['tasks'][0]['cost_usd'] is None
    assert 'cost_estimated' in card['tasks'][0]


def test_selecting_only_a_new_model_keeps_prior_model_points(campaign):
    args, control = campaign
    runner.run_benchmark(**args)
    data = json.loads(args['config_path'].read_text())
    data['models'].append({**data['models'][0], 'id': 'model-b', 'model': 'model-b', 'provider': 'openai'})
    args['config_path'].write_text(json.dumps(data))
    control['calls'].clear()
    summary = runner.run_benchmark(**args, selected_models=['model-b'])
    assert set(summary['models']) == {'model-a', 'model-b'}
    assert summary['models']['model-a']['completed'] == summary['models']['model-b']['completed'] == 3
    assert all(model == 'model-b' for model, _ in control['calls'])
    old_card = json.loads((args['output_dir'] / 'test' / 'scorecard_model-a.json').read_text())
    assert old_card['provider'] == summary['models']['model-a']['provider'] == 'google'
    assert old_card['max_output_tokens'] == summary['models']['model-a']['max_output_tokens'] == 1000


def test_finished_subset_is_partial_instead_of_still_running(campaign):
    args, _ = campaign
    summary = runner.run_benchmark(**args, max_tasks=1)
    assert summary['status'] == 'partial'
    assert summary['models']['model-a']['status'] == 'partial'


def test_manifest_reordering_preserves_the_seeded_resume_cohort(campaign):
    args, control = campaign
    first = runner.run_benchmark(**args, max_tasks=1)
    items = json.loads(args['manifest_path'].read_text())
    args['manifest_path'].write_text(json.dumps(list(reversed(items))))
    second = runner.run_benchmark(**args, max_tasks=1)
    assert second['dataset_fingerprint'] == first['dataset_fingerprint']
    assert len(control['calls']) == 1
    assert second['models']['model-a']['completed'] == 1


@pytest.mark.parametrize('replace_error_with_priced_success', [False, True])
@pytest.mark.parametrize('include_cost_field', [False, True])
def test_capped_resume_refuses_unknown_historical_costs_even_for_other_models(campaign, replace_error_with_priced_success, include_cost_field):
    args, control = campaign
    runner.run_benchmark(**args, max_tasks=1)
    with RunStore(args['output_dir'] / 'test' / 'state.sqlite3') as store:
        error = {'error': 'timeout', 'error_kind': 'unavailable'}
        if include_cost_field:
            error['cost_usd'] = None
        store.save_result('test', 'model-a', 'two', error)
        if replace_error_with_priced_success:
            item = next(item for item in runner.load_manifest(str(args['manifest_path'])) if item['taskId'] == 'two')
            client = BaselineEvaluator(model_name='model-a', mock=True)
            result = asdict(control['result'](client, item, item['prompt']))
            result['cost_usd'] = 0.00011
            store.save_result('test', 'model-a', 'two', result)
            client.close()
    data = json.loads(args['config_path'].read_text())
    data['models'].append({**data['models'][0], 'id': 'model-b', 'model': 'model-b'})
    args['config_path'].write_text(json.dumps(data))
    control['calls'].clear()
    with pytest.raises(ValueError, match='unknown|unresolved'):
        runner.run_benchmark(**args, selected_models=['model-b'])
    assert control['calls'] == []


def test_temporary_budget_reservations_do_not_discard_pending_tasks(campaign):
    args, control = campaign
    args['budget_usd'] = 0.013
    summary = runner.run_benchmark(**args)
    assert summary['status'] == 'complete'
    assert len(control['calls']) == 3
    assert summary['models']['model-a']['completed'] == 3
    assert summary['spent_cost_usd'] == pytest.approx(0.00033)


def test_credits_pause_sibling_models_but_other_providers_continue(campaign):
    args, control = campaign
    data = json.loads(args['config_path'].read_text())
    model = data['models'][0]
    data['models'].extend([{**model, 'id': 'model-b', 'model': 'model-b'},
                           {**model, 'id': 'model-c', 'model': 'model-c', 'provider': 'openai'}])
    args['config_path'].write_text(json.dumps(data))
    args['concurrency'] = 1

    def evaluate(client, item, prompt):
        result = control['result'](client, item, prompt)
        return replace(result, error='credits exhausted', error_kind='credits') if client.model_name == 'model-a' else result

    control['evaluate'] = evaluate
    summary = runner.run_benchmark(**args)
    assert [model for model, _ in control['calls']].count('model-a') == 1
    assert [model for model, _ in control['calls']].count('model-b') == 0
    assert [model for model, _ in control['calls']].count('model-c') == 3
    assert summary['models']['model-a']['status'] == summary['models']['model-b']['status'] == 'paused'
    assert summary['models']['model-c']['status'] == 'complete'


def test_unclassified_request_failure_pauses_the_model(campaign):
    args, control = campaign
    args['concurrency'] = 1

    def evaluate(client, item, prompt):
        return replace(control['result'](client, item, prompt), error='HTTP 400: invalid parameter', error_kind='other')

    control['evaluate'] = evaluate
    summary = runner.run_benchmark(**args)
    assert len(control['calls']) == 1
    assert summary['models']['model-a']['status'] == 'paused'
