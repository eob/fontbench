"""Frozen release identities and rejection of unsafe publication claims."""

import importlib.util
import json
from pathlib import Path

import pytest


def test_release_identity_api_is_available():
    assert importlib.util.find_spec('baseline.releases') is not None, 'Versioned release identity API is missing'


def test_frozen_v1_descriptor_exists_and_names_a_git_commit():
    path = Path(__file__).resolve().parents[1] / 'releases/1.0.0.json'
    assert path.is_file(), 'FontBench V1.0.0 release descriptor is missing'
    descriptor = json.loads(path.read_text())
    assert descriptor['benchmark_version'] == '1.0.0'
    assert descriptor['dataset_git_commit'] == 'd69e87e2c206ea75c52f5b8340d677bd14af03e3'


@pytest.fixture
def frozen_release(tmp_path):
    import subprocess
    from PIL import Image
    from baseline.evaluator import dataset_fingerprint, evaluation_protocol_fingerprint, load_manifest

    data = tmp_path / 'dataset/frozen'
    data.mkdir(parents=True)
    Image.new('RGB', (4, 4), 'white').save(data / 'sample.png')
    sample = dict(taskId='one', fontId='arial', fontName='Arial', aliases=[], category='non-serif',
                  weight='regular', modifier='regular', kerning='normal', lineHeight='normal',
                  widthId='narrow', widthPx=220, imageFilename='sample.png', prompt='Identify the typography.')
    manifest = data / 'manifest.json'
    manifest.write_text(json.dumps([sample]))
    for command in (['git', 'init', '-q'], ['git', 'add', 'dataset'],
                    ['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'Freeze fixture']):
        subprocess.run(command, cwd=tmp_path, check=True, capture_output=True)
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=tmp_path, check=True, text=True, capture_output=True).stdout.strip()
    descriptor = dict(schema_version=1, benchmark_version='1.0.0', dataset_manifest='dataset/frozen/manifest.json',
                      dataset_git_path='dataset/frozen', harbor_dataset='dataset/harbor', dataset_git_commit=commit,
                      dataset_fingerprint=dataset_fingerprint(load_manifest(str(manifest))),
                      evaluation_protocol_fingerprint=evaluation_protocol_fingerprint(), expected_task_count=1)
    (tmp_path / 'releases').mkdir()
    (tmp_path / 'releases/1.0.0.json').write_text(json.dumps(descriptor))
    return tmp_path, descriptor


def test_release_validates_exact_git_data_and_protocol(frozen_release):
    from baseline.releases import load_release, validate_release
    root, descriptor = frozen_release
    loaded = load_release('1.0.0', root=root)
    assert loaded == descriptor
    assert [item['taskId'] for item in validate_release(loaded, root=root)] == ['one']


@pytest.mark.parametrize('version', ['../1.0.0', 'v1.0.0', '1.0.0/', '01.0.0', '1.0', '', '1.0.0\n'])
def test_release_version_rejects_aliases_and_path_traversal(version, tmp_path):
    from baseline.releases import load_release
    with pytest.raises(ValueError, match='semantic version'):
        load_release(version, root=tmp_path)


@pytest.mark.parametrize(('key', 'value'), [
    ('schema_version', True), ('schema_version', 2), ('benchmark_version', '2.0.0'),
    ('dataset_git_commit', 'd69e87e'), ('dataset_fingerprint', 'a' * 63),
    ('evaluation_protocol_fingerprint', 'A' * 64), ('expected_task_count', True),
    ('expected_task_count', 0), ('dataset_manifest', '/tmp/manifest.json'),
    ('dataset_manifest', '../manifest.json'), ('dataset_git_path', 'dataset//frozen'),
    ('dataset_git_path', 'dataset/other'), ('harbor_dataset', '../other'),
])
def test_release_descriptor_rejects_invalid_identity(frozen_release, key, value):
    from baseline.releases import load_release
    root, descriptor = frozen_release
    descriptor[key] = value
    (root / 'releases/1.0.0.json').write_text(json.dumps(descriptor))
    with pytest.raises(ValueError):
        load_release('1.0.0', root=root)


@pytest.mark.parametrize(('key', 'value', 'message'), [
    ('evaluation_protocol_fingerprint', '0' * 64, 'protocol'),
    ('dataset_fingerprint', '0' * 64, 'fingerprint'),
    ('expected_task_count', 2, 'task count'),
    ('dataset_git_commit', '0' * 40, 'Git commit'),
])
def test_release_rejects_changed_provenance(frozen_release, key, value, message):
    from baseline.releases import validate_release
    root, descriptor = frozen_release
    descriptor[key] = value
    with pytest.raises(ValueError, match=message):
        validate_release(descriptor, root=root)


def test_release_rejects_manifest_edits_even_when_fingerprint_is_recomputed(frozen_release):
    from baseline.evaluator import dataset_fingerprint, load_manifest
    from baseline.releases import validate_release
    root, descriptor = frozen_release
    path = root / descriptor['dataset_manifest']
    samples = json.loads(path.read_text())
    samples[0]['fontName'] = 'A different target'
    path.write_text(json.dumps(samples))
    descriptor['dataset_fingerprint'] = dataset_fingerprint(load_manifest(str(path)))
    with pytest.raises(ValueError, match='recorded Git commit'):
        validate_release(descriptor, root=root)


def test_release_rejects_changed_image_bytes(frozen_release):
    from PIL import Image
    from baseline.releases import validate_release
    root, descriptor = frozen_release
    Image.new('RGB', (4, 4), 'black').save(root / 'dataset/frozen/sample.png')
    with pytest.raises(ValueError, match='fingerprint'):
        validate_release(descriptor, root=root)


def test_release_rejects_custom_manifest_path(frozen_release):
    from baseline.releases import validate_release
    root, descriptor = frozen_release
    with pytest.raises(ValueError, match='custom manifest'):
        validate_release(descriptor, root / 'other.json', root=root)


def test_release_rejects_manifest_symlink_escape(frozen_release, tmp_path_factory):
    from baseline.releases import release_manifest_path
    root, descriptor = frozen_release
    manifest = root / descriptor['dataset_manifest']
    external = tmp_path_factory.mktemp('external') / 'manifest.json'
    external.write_bytes(manifest.read_bytes())
    manifest.unlink()
    manifest.symlink_to(external)
    with pytest.raises(ValueError, match='outside the repository'):
        release_manifest_path(descriptor, root=root)


def test_inference_identity_ignores_catalog_metadata_and_normalizes_endpoint():
    from baseline.releases import model_config_fingerprint
    model = dict(provider='openai', model='custom/model', base_url='https://example.com/v1/',
                 id='old', input_per_m=1.0, display_name='Old')
    equivalent = {**model, 'id': 'new', 'display_name': 'New', 'input_per_m': 2.0,
                  'base_url': 'https://example.com/v1', 'max_output_tokens': 1024}
    assert model_config_fingerprint(model) == model_config_fingerprint(equivalent)
    for key, value in [('provider', 'google'), ('model', 'other'),
                       ('base_url', 'https://other.example.com/v1'), ('max_output_tokens', 2048)]:
        assert model_config_fingerprint(model) != model_config_fingerprint({**model, key: value})


def test_inference_identity_resolves_default_provider_endpoints():
    from baseline.providers import PROVIDERS
    from baseline.releases import model_config_fingerprint
    for provider, (endpoint, _) in PROVIDERS.items():
        implicit = dict(provider=provider, model='model')
        explicit = {**implicit, 'base_url': endpoint + '/'}
        assert model_config_fingerprint(implicit) == model_config_fingerprint(explicit)
