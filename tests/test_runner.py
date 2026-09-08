"""Checkpointed benchmark orchestration without remote requests."""

import json
from dataclasses import replace
from unittest.mock import Mock

import pytest
from PIL import Image

from baseline.evaluator import BaselineEvaluator
from baseline.runner import run_benchmark


@pytest.fixture
def benchmark(tmp_path):
    Image.new('RGB', (4, 4), 'white').save(tmp_path / 'sample.png')
    sample = dict(taskId='one', fontId='arial', fontName='Arial', aliases=[], category='non-serif',
                  weight='regular', modifier='regular', kerning='normal', lineHeight='normal',
                  widthId='narrow', widthPx=220, imageFilename='sample.png', prompt='Identify the typography.')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps([sample, {**sample, 'taskId': 'two'}]))
    config = tmp_path / 'models.json'
    model = dict(id='model-a', provider='google', model='model-a', display_name='A', enabled=True,
                 api_key_env='TEST_KEY', source_url='https://example.com/models', max_output_tokens=1024, input_per_m=1.0, output_per_m=1.0)
    config.write_text(json.dumps(dict(version=1, verified_at='2026-09-07', models=[model])))
    return dict(manifest_path=manifest, config_path=config, output_dir=tmp_path / 'runs', run_id='test', mock=True)


def test_resume_does_not_repeat_completed_tasks(benchmark, monkeypatch):
    calls = []
    original = BaselineEvaluator._eval_single_task
    def evaluate(self, item, prompt):
        calls.append(item['taskId'])
        return original(self, item, prompt)
    monkeypatch.setattr(BaselineEvaluator, '_eval_single_task', evaluate)
    first = run_benchmark(**benchmark)
    second = run_benchmark(**benchmark)
    assert first['models']['model-a']['completed'] == 2
    assert second['models']['model-a']['completed'] == 2
    assert len(calls) == 2


def test_adding_a_model_preserves_previous_datapoints(benchmark, monkeypatch):
    run_benchmark(**benchmark)
    config = json.loads(benchmark['config_path'].read_text())
    config['models'].append({**config['models'][0], 'id': 'model-b', 'model': 'model-b'})
    benchmark['config_path'].write_text(json.dumps(config))
    calls = []
    original = BaselineEvaluator._eval_single_task
    def evaluate(self, item, prompt):
        calls.append(self.model_name)
        return original(self, item, prompt)
    monkeypatch.setattr(BaselineEvaluator, '_eval_single_task', evaluate)
    result = run_benchmark(**benchmark)
    assert calls == ['model-b', 'model-b']
    assert result['models']['model-a']['completed'] == result['models']['model-b']['completed'] == 2


def test_changed_images_cannot_resume_as_the_same_benchmark(benchmark):
    run_benchmark(**benchmark)
    Image.new('RGB', (4, 4), 'black').save(benchmark['manifest_path'].parent / 'sample.png')
    with pytest.raises(ValueError, match='fingerprint|dataset'):
        run_benchmark(**benchmark)


def test_interrupted_partial_run_resumes_remaining_tasks(benchmark):
    first = run_benchmark(**benchmark, max_tasks=1)
    assert first['models']['model-a']['completed'] == 1
    second = run_benchmark(**benchmark)
    assert second['models']['model-a']['completed'] == 2


def test_zero_budget_never_calls_a_provider(benchmark, monkeypatch):
    benchmark['mock'] = False
    monkeypatch.setattr('baseline.validate_dataset.require_valid_dataset', lambda path: {'valid': True})
    def fail(*args, **kwargs):
        raise AssertionError('No paid request should start')
    monkeypatch.setattr(BaselineEvaluator, '_eval_single_task', fail)
    result = run_benchmark(**benchmark, budget_usd=0)
    assert result['status'] == 'budget_exhausted'
    assert result['models']['model-a']['completed'] == 0


def test_changed_evaluation_protocol_cannot_resume(benchmark, monkeypatch):
    import baseline.evaluator as evaluator_module
    run_benchmark(**benchmark, max_tasks=1)
    monkeypatch.setattr(evaluator_module, 'DEFAULT_PROMPT', 'A changed evaluation prompt', raising=False)
    with pytest.raises(ValueError, match='fingerprint|protocol'):
        run_benchmark(**benchmark)


def test_changed_rendering_evidence_changes_dataset_identity(benchmark):
    from baseline.runner import dataset_fingerprint, load_manifest
    items = load_manifest(str(benchmark['manifest_path']))
    initial = dataset_fingerprint(items)
    items[0]['fontRendering'] = {'verified': False}
    assert dataset_fingerprint(items) != initial


def test_foreign_checkpoint_tasks_are_refused_before_resuming(benchmark, monkeypatch):
    from baseline.run_state import RunStore
    run_benchmark(**benchmark, max_tasks=1)
    with RunStore(benchmark['output_dir'] / 'mock-test' / 'state.sqlite3') as store:
        previous = next(iter(store.completed_results('test', 'model-a').values()))
        store.save_result('test', 'model-a', 'foreign-task', {**previous, 'task_id': 'foreign-task'})
    calls = []
    original = BaselineEvaluator._eval_single_task
    def evaluate(self, item, prompt):
        calls.append(item['taskId'])
        return original(self, item, prompt)
    monkeypatch.setattr(BaselineEvaluator, '_eval_single_task', evaluate)
    with pytest.raises(ValueError, match='checkpoint'):
        run_benchmark(**benchmark, max_tasks=1)
    assert calls == []


def test_live_run_requires_valid_dataset_before_client_creation(benchmark, monkeypatch):
    import baseline.runner as runner_module
    def refuse(path):
        raise ValueError('Dataset is not valid: audit evidence missing')
    monkeypatch.setattr('baseline.validate_dataset.require_valid_dataset', refuse)
    client = Mock()
    monkeypatch.setattr(runner_module, 'BaselineEvaluator', client)
    benchmark['mock'] = False
    with pytest.raises(ValueError, match='Dataset is not valid'):
        run_benchmark(**benchmark)
    client.assert_not_called()


def test_custom_manifest_ledger_does_not_claim_a_release(benchmark):
    result = run_benchmark(**benchmark)
    assert 'benchmark_version' in result, 'Runs have no explicit benchmark version identity'
    assert result['benchmark_version'] is None
    directory = benchmark['output_dir'] / 'mock-test'
    assert (directory / 'run.json').is_file()
    assert (directory / 'attempts.jsonl').is_file()
    card = json.loads((directory / 'scorecard_model-a.json').read_text())
    assert card['run_id'] == 'test'
    assert card['model_config_fingerprint'] == result['models']['model-a']['model_config_fingerprint']
    assert all(task['recorded_at'] for task in card['tasks'])


def test_default_release_uses_version_directory_and_complete_provenance(benchmark):
    from baseline.releases import load_release
    benchmark.pop('manifest_path')
    result = run_benchmark(**benchmark, max_tasks=1)
    release = load_release()
    for key in ('benchmark_version', 'dataset_git_commit', 'dataset_fingerprint', 'evaluation_protocol_fingerprint'):
        assert result[key] == release[key]
    assert result['expected_task_count'] == 1824
    assert len(result['runner_git_commit']) == 40
    assert isinstance(result['runner_git_dirty'], bool)
    directory = benchmark['output_dir'] / '1.0.0/mock-test'
    metadata = json.loads((directory / 'run.json').read_text())
    assert metadata['created_at'] == result['created_at']
    assert metadata['invocations'][0]['status'] == 'partial'
    assert metadata['invocations'][0]['models'][0]['id'] == 'model-a'
    card = json.loads((directory / 'scorecard_model-a.json').read_text())
    attempts = [json.loads(line) for line in (directory / 'attempts.jsonl').read_text().splitlines()]
    assert len(attempts) == len(card['tasks']) == 1
    assert attempts[0]['result']['recorded_at'] == card['tasks'][0]['recorded_at']
    assert attempts[0]['run_id'] == card['run_id'] == result['run_id']
    assert card['benchmark_version'] == '1.0.0'


@pytest.mark.parametrize('key', ['dataset_fingerprint', 'evaluation_protocol_fingerprint'])
def test_release_mismatch_is_refused_before_client_creation(benchmark, monkeypatch, key):
    import baseline.runner as runner_module
    from baseline.releases import load_release
    descriptor = load_release()
    descriptor[key] = '0' * 64
    monkeypatch.setattr(runner_module, 'load_release', lambda _: descriptor)
    client = Mock()
    monkeypatch.setattr(runner_module, 'BaselineEvaluator', client)
    benchmark.pop('manifest_path')
    benchmark['mock'] = False
    with pytest.raises(ValueError, match='fingerprint|protocol'):
        run_benchmark(**benchmark)
    client.assert_not_called()
    assert not benchmark['output_dir'].exists()


def test_custom_manifest_cannot_request_release_label(benchmark):
    with pytest.raises(ValueError, match='either'):
        run_benchmark(**benchmark, release='1.0.0')
    assert not benchmark['output_dir'].exists()


def test_omitting_run_id_creates_independent_ledgers(benchmark):
    benchmark.pop('run_id')
    first = run_benchmark(**benchmark, max_tasks=0)
    second = run_benchmark(**benchmark, max_tasks=0)
    assert first['run_id'] != second['run_id']
    assert (benchmark['output_dir'] / f"mock-{first['run_id']}" / 'run.json').is_file()
    assert (benchmark['output_dir'] / f"mock-{second['run_id']}" / 'run.json').is_file()


def test_resume_preserves_creation_and_observation_times_and_logs_invocations(benchmark):
    first = run_benchmark(**benchmark, max_tasks=1)
    directory = benchmark['output_dir'] / 'mock-test'
    initial_card = json.loads((directory / 'scorecard_model-a.json').read_text())
    second = run_benchmark(**benchmark)
    final_card = json.loads((directory / 'scorecard_model-a.json').read_text())
    assert first['created_at'] == second['created_at']
    assert second['updated_at'] >= first['updated_at']
    initial_task = initial_card['tasks'][0]
    assert next(task for task in final_card['tasks'] if task['task_id'] == initial_task['task_id']) == initial_task
    metadata = json.loads((directory / 'run.json').read_text())
    assert [invocation['status'] for invocation in metadata['invocations']] == ['partial', 'complete']
    assert len((directory / 'attempts.jsonl').read_text().splitlines()) == 2


def test_resume_refuses_changed_run_metadata(benchmark, monkeypatch):
    run_benchmark(**benchmark, max_tasks=1)
    path = benchmark['output_dir'] / 'mock-test/run.json'
    metadata = json.loads(path.read_text())
    metadata['benchmark_version'] = '1.0.0'
    path.write_text(json.dumps(metadata))
    evaluate = Mock()
    monkeypatch.setattr(BaselineEvaluator, '_eval_single_task', evaluate)
    with pytest.raises(ValueError, match='metadata'):
        run_benchmark(**benchmark)
    evaluate.assert_not_called()


def test_resume_repairs_partial_attempt_export_without_repeating_requests(benchmark, monkeypatch):
    run_benchmark(**benchmark)
    path = benchmark['output_dir'] / 'mock-test/attempts.jsonl'
    original = path.read_bytes()
    path.write_text('{partial JSON')
    evaluate = Mock()
    monkeypatch.setattr(BaselineEvaluator, '_eval_single_task', evaluate)
    run_benchmark(**benchmark)
    assert path.read_bytes() == original
    evaluate.assert_not_called()


@pytest.mark.parametrize('corruption', ['missing', 'creation', 'object-invocations', 'empty-invocations', 'invalid-invocation'])
def test_resume_refuses_lost_or_corrupt_invocation_history_before_inference(benchmark, monkeypatch, corruption):
    run_benchmark(**benchmark, max_tasks=1)
    path = benchmark['output_dir'] / 'mock-test/run.json'
    metadata = json.loads(path.read_text())
    if corruption == 'missing':
        path.unlink()
    else:
        if corruption == 'creation':
            metadata['created_at'] = '2000-01-01T00:00:00Z'
        elif corruption == 'object-invocations':
            metadata['invocations'] = {}
        elif corruption == 'empty-invocations':
            metadata['invocations'] = []
        else:
            metadata['invocations'] = [None]
        path.write_text(json.dumps(metadata))
    evaluate = Mock(side_effect=AssertionError('No inference after lost or corrupt provenance'))
    monkeypatch.setattr(BaselineEvaluator, '_eval_single_task', evaluate)
    with pytest.raises(ValueError, match='metadata|invocation|history'):
        run_benchmark(**benchmark)
    evaluate.assert_not_called()


def test_brand_new_empty_checkpoint_recovers_without_run_metadata(benchmark):
    from baseline.run_state import RunStore
    path = benchmark['output_dir'] / 'mock-test/state.sqlite3'
    with RunStore(path):
        pass
    result = run_benchmark(**benchmark)
    assert result['models']['model-a']['completed'] == 2
    assert (path.parent / 'run.json').is_file()


def test_initialized_zero_task_run_needs_its_retained_history(benchmark, monkeypatch):
    run_benchmark(**benchmark, max_tasks=0)
    (benchmark['output_dir'] / 'mock-test/run.json').unlink()
    evaluate = Mock()
    monkeypatch.setattr(BaselineEvaluator, '_eval_single_task', evaluate)
    with pytest.raises(ValueError, match='lost run metadata'):
        run_benchmark(**benchmark)
    evaluate.assert_not_called()


def test_resume_refuses_history_that_dropped_an_earlier_model(benchmark, monkeypatch):
    run_benchmark(**benchmark, max_tasks=1)
    config = json.loads(benchmark['config_path'].read_text())
    config['models'].append({**config['models'][0], 'id': 'model-b', 'model': 'model-b'})
    benchmark['config_path'].write_text(json.dumps(config))
    run_benchmark(**benchmark, max_tasks=1, selected_models=['model-b'])
    path = benchmark['output_dir'] / 'mock-test/run.json'
    metadata = json.loads(path.read_text())
    metadata['invocations'] = metadata['invocations'][-1:]
    path.write_text(json.dumps(metadata))
    evaluate = Mock()
    monkeypatch.setattr(BaselineEvaluator, '_eval_single_task', evaluate)
    with pytest.raises(ValueError, match='lost a checkpoint model'):
        run_benchmark(**benchmark, selected_models=['model-b'])
    evaluate.assert_not_called()
