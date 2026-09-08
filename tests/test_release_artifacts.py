"""Check the packaged release against its frozen rendering, across every task."""

import hashlib
import json
from pathlib import Path

import tomlkit


def test_packaged_release_matches_every_frozen_input():
    root = Path(__file__).resolve().parents[1]
    rendered = root / 'dataset/fontbench-2-rendered'
    package = root / 'dataset/fontbench-2'
    samples = {row['taskId']: row for row in json.loads((rendered / 'manifest.json').read_text())}
    descriptor = tomlkit.parse((package / 'dataset.toml').read_text())
    assert descriptor['dataset']['name'] == 'fontbench-2'
    assert descriptor['metadata']['total_tasks'] == len(samples)
    prompt = (root / 'baseline/prompt.txt').read_text().strip()
    seen = set()
    instructions = set()
    for directory in (package / 'tasks').iterdir():
        truth = json.loads((directory / 'tests/ground_truth.json').read_text())
        sample = samples[truth['taskId']]
        assert truth['taskId'] not in seen
        seen.add(truth['taskId'])
        assert directory.name == truth['harborTaskId']
        assert directory.name.startswith('task-')
        assert hashlib.sha256((directory / 'environment/sample.png').read_bytes()).hexdigest() == sample['imageSha256']
        assert truth['canonical'] == sample['fontName']
        for key in ('aliases', 'category', 'weight', 'modifier', 'kerning', 'lineHeight', 'widthId', 'widthPx'):
            assert truth[key] == sample[key]
        instructions.add((directory / 'instruction.md').read_text())
        config = tomlkit.parse((directory / 'task.toml').read_text())
        assert config['metadata']['name'] == directory.name
        assert config['metadata']['tags'] == ['typography', 'font-identification', 'vlm']
    assert seen == set(samples)
    assert len(instructions) == 1
    assert prompt in instructions.pop()
