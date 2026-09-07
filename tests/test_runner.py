"""Checkpointed benchmark orchestration without remote requests."""

import json
from dataclasses import replace

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
    def fail(*args, **kwargs):
        raise AssertionError('No paid request should start')
    monkeypatch.setattr(BaselineEvaluator, '_eval_single_task', fail)
    result = run_benchmark(**benchmark, budget_usd=0)
    assert result['status'] == 'budget_exhausted'
    assert result['models']['model-a']['completed'] == 0
