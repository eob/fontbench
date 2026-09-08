"""Frozen benchmark releases and public inference configuration identities."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any

from baseline.evaluator import dataset_fingerprint, evaluation_protocol_fingerprint, load_manifest
from baseline.providers import PROVIDERS


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE = '1.0.0'
_VERSION = r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'


def load_release(version: str = DEFAULT_RELEASE, *, root: str | Path | None = None) -> dict[str, Any]:
    """Read a semantic version descriptor without accessing models or API keys."""
    if not isinstance(version, str) or re.fullmatch(_VERSION, version) is None:
        raise ValueError('Release must be an exact semantic version, for example 1.0.0')
    path = Path(root or REPO_ROOT) / 'releases' / f'{version}.json'
    try:
        descriptor = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f'Cannot load FontBench release {version}: {error}') from error
    if not isinstance(descriptor, dict) or type(descriptor.get('schema_version')) is not int or descriptor['schema_version'] != 1:
        raise ValueError('Unsupported release descriptor schema_version')
    if descriptor.get('benchmark_version') != version:
        raise ValueError('Release filename and benchmark_version disagree')
    for key, length in [('dataset_fingerprint', 64), ('evaluation_protocol_fingerprint', 64), ('dataset_git_commit', 40)]:
        if not isinstance(descriptor.get(key), str) or re.fullmatch(r'[0-9a-f]{' + str(length) + '}', descriptor[key]) is None:
            raise ValueError(f'Release {key} must be a complete lowercase hexadecimal hash')
    for key in ('dataset_manifest', 'dataset_git_path', 'harbor_dataset'):
        value = descriptor.get(key)
        if not isinstance(value, str) or not value or '\\' in value:
            raise ValueError(f'Release {key} must be a repository-relative path')
        parsed = PurePosixPath(value)
        if parsed.is_absolute() or '..' in parsed.parts or str(parsed) != value:
            raise ValueError(f'Release {key} must be a normalized repository-relative path')
    if descriptor['dataset_manifest'] != descriptor['dataset_git_path'] + '/manifest.json':
        raise ValueError('Release manifest must belong to dataset_git_path')
    if type(descriptor.get('expected_task_count')) is not int or descriptor['expected_task_count'] < 1:
        raise ValueError('Release expected_task_count must be a positive integer')
    return descriptor


def release_manifest_path(release: dict, *, root: str | Path | None = None) -> Path:
    repository = Path(root or REPO_ROOT).resolve()
    manifest = (repository / release['dataset_manifest']).resolve()
    if not manifest.is_relative_to(repository):
        raise ValueError('Release manifest resolves outside the repository')
    return manifest


def validate_release(
    release: dict, manifest_path: str | Path | None = None, *,
    root: str | Path | None = None, items: list[dict] | None = None,
) -> list[dict]:
    """Refuse changed release data, Git provenance, or evaluation code."""
    repository = Path(root or REPO_ROOT).resolve()
    manifest = release_manifest_path(release, root=repository)
    if manifest_path is not None and Path(manifest_path).resolve() != manifest:
        raise ValueError('A custom manifest cannot be labeled as a frozen release')
    if evaluation_protocol_fingerprint() != release['evaluation_protocol_fingerprint']:
        raise ValueError('Evaluation protocol differs from the frozen release; use its compatible code checkout')
    try:
        committed = subprocess.run(
            ['git', 'show', f"{release['dataset_git_commit']}:{release['dataset_manifest']}"],
            cwd=repository, capture_output=True, check=True,
        ).stdout
        current = manifest.read_bytes()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError('Cannot verify release dataset Git commit and manifest') from error
    if committed != current:
        raise ValueError('Dataset manifest differs from its recorded Git commit')
    items = load_manifest(str(manifest)) if items is None else items
    if len(items) != release['expected_task_count']:
        raise ValueError('Dataset task count differs from the frozen release')
    if dataset_fingerprint(items) != release['dataset_fingerprint']:
        raise ValueError('Dataset fingerprint differs from the frozen release')
    return items


def model_config_fingerprint(model: dict) -> str:
    """Group the same inference setup even when catalog labels or prices change."""
    configuration = {key: model[key] for key in ('provider', 'model')}
    configuration['base_url'] = (model.get('base_url') or PROVIDERS[model['provider']][0]).rstrip('/')
    configuration['max_output_tokens'] = model.get('max_output_tokens', 1024)
    return hashlib.sha256(json.dumps(configuration, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def git_code_identity(*, root: str | Path | None = None) -> dict:
    repository = Path(root or REPO_ROOT)
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repository, text=True, capture_output=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(['git', 'status', '--porcelain'], cwd=repository, text=True, capture_output=True, check=True).stdout)
    except (OSError, subprocess.CalledProcessError):
        return {'runner_git_commit': None, 'runner_git_dirty': None}
    return {'runner_git_commit': commit, 'runner_git_dirty': dirty}


def main() -> None:
    import argparse
    from baseline.validate_dataset import require_valid_dataset

    parser = argparse.ArgumentParser(description='Validate a frozen FontBench release and print its identity')
    parser.add_argument('--release', default=DEFAULT_RELEASE)
    args = parser.parse_args()
    release = load_release(args.release)
    validate_release(release)
    require_valid_dataset(release_manifest_path(release))
    print(json.dumps(release, indent=2))


if __name__ == '__main__':
    main()
