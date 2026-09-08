import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from baseline.validate_dataset import require_valid_dataset, validate_dataset


@pytest.fixture
def candidate(tmp_path):
    image = Image.new('RGB', (440, 228), 'white')
    draw = ImageDraw.Draw(image)
    draw.rectangle((52, 58, 200, 80), fill='#111827')
    draw.rectangle((52, 122, 200, 144), fill='#111827')
    image.save(tmp_path / 'sample.png')
    (tmp_path / 'fonts').mkdir()
    asset = tmp_path / 'fonts/fixture.woff'
    asset.write_bytes((Path(__file__).parent / 'fixtures/fixture.woff').read_bytes())
    sample = {
        'taskId': 'font-fixture-v01', 'fontId': 'fixture', 'fontName': 'Fixture Sans',
        'category': 'non-serif', 'aliases': ['fixture sans'], 'weight': 'regular',
        'weightNumeric': 400, 'modifier': 'regular', 'kerning': 'normal',
        'lineHeight': 'normal', 'widthId': 'narrow', 'widthPx': 220,
        'imageFilename': 'sample.png', 'imageSha256': hashlib.sha256((tmp_path / 'sample.png').read_bytes()).hexdigest(),
        'pangram': 'The quick brown fox\njumps over the lazy dog.', 'prompt': 'Identify the six typographic properties.',
        'layout': {'lineCount': 2, 'lineBoxes': [
            {'x': 25, 'y': 25, 'width': 150, 'height': 25},
            {'x': 25, 'y': 56.9, 'width': 150, 'height': 25}],
            'contentWidthPx': 170, 'cardWidthPx': 220, 'cardHeightPx': 114,
            'fontSizePx': 22, 'lineHeightPx': 31.9, 'letterSpacingPx': 0, 'deviceScaleFactor': 2},
        'fontRendering': {
            'browserVersion': 'test', 'syntheticItalic': False, 'smallCapsSynthesisAllowed': False,
            'loadedFaces': [{'family': 'Fixture Sans', 'weight': '400', 'style': 'normal'}],
            'platformFonts': [{'familyName': 'Fixture Sans', 'postScriptName': 'FixtureSans-Regular', 'isCustomFont': True, 'glyphCount': 43}],
            'assets': [{'path': 'fonts/fixture.woff', 'url': 'https://example.test/font.woff',
                        'sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
                        'familyName': 'Fixture Sans', 'postscriptName': 'FixtureSans-Regular',
                        'typographicFamily': 'Fixture Sans', 'subfamilyName': 'Regular',
                        'weight': 400, 'weightRange': [400, 400], 'italic': False}],
        },
    }
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps([sample]))
    (tmp_path / 'catalog.json').write_text(json.dumps({
        'fonts': [{'id': 'fixture', 'name': 'Fixture Sans', 'cssFamily': 'Fixture Sans', 'category': 'non-serif', 'aliases': ['fixture sans']}],
        'recipes': [{'variantIndex': 1, 'weight': 'regular', 'modifier': 'regular', 'kerning': 'normal', 'lineHeight': 'normal', 'widthId': 'narrow'}],
        'pangram': sample['pangram'], 'prompt': sample['prompt'],
    }))
    (tmp_path / 'skipped.json').write_text('[]')
    return manifest


def change(candidate, mutate):
    rows = json.loads(candidate.read_text())
    mutate(rows)
    candidate.write_text(json.dumps(rows))


def test_complete_evidence_passes(candidate):
    report = require_valid_dataset(candidate)
    assert report['valid'] is True
    assert report['sample_count'] == 1
    assert report['errors'] == []


@pytest.mark.parametrize(('mutate', 'code'), [
    (lambda rows: rows[0].pop('layout'), 'layout'),
    (lambda rows: rows[0]['layout'].update(lineCount=1), 'layout'),
    (lambda rows: rows[0]['layout'].update(lineHeightPx=42), 'layout'),
    (lambda rows: rows[0]['layout'].update(letterSpacingPx=2.64), 'layout'),
    (lambda rows: rows[0]['layout'].update(deviceScaleFactor=1), 'layout'),
    (lambda rows: rows[0]['layout']['lineBoxes'][1].update(x=-3), 'layout'),
    (lambda rows: rows[0].update(imageSha256='0' * 64), 'image_hash'),
    (lambda rows: rows[0]['fontRendering'].update(syntheticItalic=True), 'font_provenance'),
    (lambda rows: rows[0]['fontRendering']['platformFonts'][0].update(isCustomFont=False), 'font_provenance'),
    (lambda rows: rows[0]['fontRendering']['assets'][0].update(sha256='0' * 64), 'font_asset'),
    (lambda rows: rows[0]['fontRendering']['assets'][0].update(path='../outside.woff'), 'font_asset'),
    (lambda rows: rows[0]['fontRendering']['assets'][0].update(familyName='Wrong Font'), 'font_asset'),
    (lambda rows: rows[0].update(weight='black', weightNumeric=900), 'font_provenance'),
    (lambda rows: rows.append({**rows[0], 'taskId': 'duplicate'}), 'duplicate_pixels'),
    (lambda rows: rows[0].update(prompt='The answer is Fixture Sans'), 'prompt'),
])
def test_rejects_invalid_evidence(candidate, mutate, code):
    change(candidate, mutate)
    report = validate_dataset(candidate)
    assert not report['valid']
    assert code in {error['code'] for error in report['errors']}
    with pytest.raises(ValueError, match='Dataset validation failed'):
        require_valid_dataset(candidate)


def test_changed_font_bytes_rejected(candidate):
    (candidate.parent / 'fonts/fixture.woff').write_bytes(b'changed')
    assert 'font_asset' in {error['code'] for error in validate_dataset(candidate)['errors']}


def test_corrupt_and_blank_png_rejected(candidate):
    image = candidate.parent / 'sample.png'
    image.write_bytes(b'not a png')
    assert 'image' in {error['code'] for error in validate_dataset(candidate)['errors']}
    Image.new('RGB', (440, 228), 'white').save(image)
    change(candidate, lambda rows: rows[0].update(imageSha256=hashlib.sha256(image.read_bytes()).hexdigest()))
    assert 'image' in {error['code'] for error in validate_dataset(candidate)['errors']}


def test_unaccounted_candidate_rejected(candidate):
    catalog = candidate.parent / 'catalog.json'
    data = json.loads(catalog.read_text())
    data['recipes'].append({**data['recipes'][0], 'variantIndex': 2})
    catalog.write_text(json.dumps(data))
    assert 'census' in {error['code'] for error in validate_dataset(candidate)['errors']}
    (candidate.parent / 'skipped.json').write_text(json.dumps([{'taskId': 'font-fixture-v02', 'reason': 'Unsupported face'}]))
    assert validate_dataset(candidate)['valid']


def test_historical_inputs_are_explicitly_unvalidated():
    root = Path(__file__).resolve().parents[1]
    report = validate_dataset(root / 'results/runs/fontbench-2026-09-07/input/manifest.json')
    assert report['sample_count'] == 639
    assert not report['valid']
    assert report['shortcut_accuracy']['widthId_to_lineHeight'] == pytest.approx(578 / 639)


def test_malformed_manifest_reports_error(tmp_path):
    manifest = tmp_path / 'manifest.json'
    manifest.write_text('{}')
    assert not validate_dataset(manifest)['valid']
    manifest.write_text('[]')
    assert not validate_dataset(manifest)['valid']


@pytest.mark.parametrize('field', ['layout', 'fontRendering'])
@pytest.mark.parametrize('value', [None, [], 1, 'invalid', {'lineCount': 2, 'lineBoxes': [None, None]}])
def test_malformed_evidence_reports_error(candidate, field, value):
    change(candidate, lambda rows: rows[0].update({field: value}))
    assert not validate_dataset(candidate)['valid']


def test_erased_second_line_cannot_claim_wrapped_text(candidate):
    file = candidate.parent / 'sample.png'
    with Image.open(file) as original:
        image = original.copy()
    ImageDraw.Draw(image).rectangle((0, 100, 440, 228), fill='white')
    image.save(file)
    change(candidate, lambda rows: rows[0].update(imageSha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    report = validate_dataset(candidate)
    assert not report['valid']
    assert 'layout' in report['error_counts']


@pytest.mark.parametrize('mode', ['LA', 'RGBA', 'P'])
def test_invisible_png_pixels_are_rejected_in_every_mode(candidate, mode):
    file = candidate.parent / 'sample.png'
    with Image.open(file) as original:
        image = original.convert(mode)
    if mode == 'P':
        image.info['transparency'] = bytes([0] * 256)
    else:
        image.putalpha(0)
    image.save(file)
    change(candidate, lambda rows: rows[0].update(imageSha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    assert not validate_dataset(candidate)['valid']


@pytest.mark.parametrize('catalog', [None, [], 1, 'invalid'])
def test_malformed_catalog_returns_findings(candidate, catalog):
    (candidate.parent / 'catalog.json').write_text(json.dumps(catalog))
    report = validate_dataset(candidate)
    assert not report['valid']
    assert 'census' in report['error_counts']


def test_hash_consistent_non_font_bytes_are_rejected(candidate):
    asset = candidate.parent / 'fonts/fixture.woff'
    asset.write_bytes(b'not a font')
    change(candidate, lambda rows: rows[0]['fontRendering']['assets'][0].update(sha256=hashlib.sha256(asset.read_bytes()).hexdigest()))
    report = validate_dataset(candidate)
    assert not report['valid']
    assert 'font_asset' in report['error_counts']


@pytest.mark.parametrize('field,value', [('familyName', 'Impostor Sans'), ('weight', 900), ('italic', True)])
def test_claimed_font_properties_must_match_actual_binary(candidate, field, value):
    change(candidate, lambda rows: rows[0]['fontRendering']['assets'][0].update({field: value}))
    catalog = candidate.parent / 'catalog.json'
    data = json.loads(catalog.read_text())
    if field == 'familyName':
        change(candidate, lambda rows: rows[0].update(fontName=value))
        data['fonts'][0]['name'] = value
    elif field == 'weight':
        change(candidate, lambda rows: rows[0].update(weight='black', weightNumeric=900))
        change(candidate, lambda rows: rows[0]['fontRendering']['loadedFaces'][0].update(weight='900'))
        change(candidate, lambda rows: rows[0]['fontRendering']['assets'][0].update(weightRange=[900, 900]))
        data['recipes'][0]['weight'] = 'black'
    else:
        change(candidate, lambda rows: rows[0].update(modifier='italic'))
        change(candidate, lambda rows: rows[0]['fontRendering']['loadedFaces'][0].update(style='italic'))
        data['recipes'][0]['modifier'] = 'italic'
    catalog.write_text(json.dumps(data))
    report = validate_dataset(candidate)
    assert not report['valid']
    assert 'font_asset' in report['error_counts']
