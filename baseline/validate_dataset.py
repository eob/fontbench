"""Offline release gate for rendered pixels, labels, and frozen font evidence."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import math
from pathlib import Path
import re

from PIL import Image, ImageChops
from fontTools.ttLib import TTFont


WEIGHTS = {'thin': 200, 'regular': 400, 'bold': 700, 'black': 900}
LINE_HEIGHTS = {'tight': 1.15, 'normal': 1.45, 'loose': 1.9}
TRACKING = {'tight': -1.1, 'normal': 0, 'loose': 2.64}
WIDTHS = {'narrow': 220, 'medium': 320, 'wide': 440}
AXES = ('fontName', 'category', 'weight', 'modifier', 'kerning', 'lineHeight', 'widthId')


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _local_file(root: Path, filename: str) -> Path:
    if not isinstance(filename, str) or not filename or Path(filename).is_absolute():
        raise ValueError('Expected a relative artifact path')
    file = (root / filename).resolve()
    if not file.is_relative_to(root) or not file.is_file():
        raise ValueError(f'Missing artifact or path outside dataset: {filename}')
    return file


def _normalize(value: str) -> str:
    return re.sub('[^a-z0-9]', '', value.lower())


def _font_metadata(raw: bytes) -> dict:
    try:
        with TTFont(io.BytesIO(raw)) as font:
            names = font['name']
            weight = font['OS/2'].usWeightClass
            weight_axis = next((axis for axis in font['fvar'].axes if axis.axisTag == 'wght'), None) if 'fvar' in font else None
            return {
                'sha256': hashlib.sha256(raw).hexdigest(),
                'familyName': names.getDebugName(1), 'subfamilyName': names.getDebugName(2),
                'typographicFamily': names.getDebugName(16) or names.getDebugName(1),
                'postscriptName': names.getDebugName(6), 'weight': weight,
                'weightRange': [weight_axis.minValue, weight_axis.maxValue] if weight_axis else [weight, weight],
                'italic': bool(font['OS/2'].fsSelection & ((1 << 0) | (1 << 9)) or font['post'].italicAngle != 0),
            }
    except Exception as error:
        raise ValueError(f'Cannot parse frozen font binary: {error}') from error


def validate_dataset(manifest_path: str | Path) -> dict:
    """Return a complete audit report; legacy inputs fail without changing files."""
    from baseline.evaluator import load_manifest

    manifest_path = Path(manifest_path).resolve()
    root = manifest_path.parent
    report = {'validation_version': 1, 'valid': False, 'sample_count': 0,
              'font_count': 0, 'errors': [], 'distributions': {}, 'shortcut_accuracy': {}}

    def fail(code: str, detail: str, task_id: str | None = None):
        report['errors'].append({'code': code, 'taskId': task_id, 'detail': detail})

    try:
        items = load_manifest(str(manifest_path))
        if not items:
            raise ValueError('Dataset is empty')
    except (ValueError, OSError, TypeError) as error:
        fail('manifest', str(error))
        return report
    report['sample_count'] = len(items)
    report['font_count'] = len({item['fontName'] for item in items})
    report['manifest_sha256'] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    report['distributions'] = {axis: dict(sorted(Counter(str(item.get(axis, '<missing>')) for item in items).items())) for axis in AXES}
    for axis in ('widthId', 'kerning'):
        groups = defaultdict(Counter)
        for item in items:
            groups[str(item.get(axis))][item['lineHeight']] += 1
        report['shortcut_accuracy'][f'{axis}_to_lineHeight'] = sum(max(group.values()) for group in groups.values()) / len(items)

    catalog = {}
    fonts = {}
    try:
        decoded_catalog = json.loads((root / 'catalog.json').read_text())
        if not isinstance(decoded_catalog, dict):
            raise ValueError('Catalog must be a JSON object')
        catalog = decoded_catalog
        fonts = {font['id']: font for font in catalog['fonts']}
        recipes = {recipe['variantIndex']: recipe for recipe in catalog['recipes']}
        if not fonts or not recipes or len(fonts) != len(catalog['fonts']) or len(recipes) != len(catalog['recipes']):
            raise ValueError('Catalog has empty or duplicate entries')
        candidates = {f'font-{font_id}-v{index:02d}': (font, recipe)
                      for font_id, font in fonts.items() for index, recipe in recipes.items()}
        skipped = json.loads((root / 'skipped.json').read_text())
        if not isinstance(skipped, list) or any(not isinstance(row, dict) or not row.get('reason') for row in skipped):
            raise ValueError('Skipped candidates must record a reason')
        skipped_ids = [row['taskId'] for row in skipped]
        rendered_ids = {item['taskId'] for item in items}
        if len(set(skipped_ids)) != len(skipped_ids) or rendered_ids & set(skipped_ids):
            raise ValueError('Duplicate or both rendered and skipped candidates')
        if rendered_ids | set(skipped_ids) != set(candidates):
            raise ValueError('Rendered and skipped IDs do not account for the frozen catalog')
        report['candidate_count'] = len(candidates)
        report['skipped_count'] = len(skipped)
        for item in items:
            font, recipe = candidates[item['taskId']]
            expected = {'fontId': font['id'], 'fontName': font['name'], 'category': font['category'],
                        'aliases': font['aliases'], **{key: recipe[key] for key in ('weight', 'modifier', 'kerning', 'lineHeight', 'widthId')}}
            if any(item.get(key) != value for key, value in expected.items()):
                fail('catalog', 'Labels differ from the frozen font catalog or recipe', item['taskId'])
        supported_groups = defaultdict(list)
        for item in items:
            supported_groups[(item['fontId'], item['weight'], item['modifier'])].append(item)
        for (_, weight, modifier), group in supported_groups.items():
            group_recipes = [recipe for recipe in recipes.values() if recipe['weight'] == weight and recipe['modifier'] == modifier]
            for axis in ('kerning', 'lineHeight', 'widthId'):
                if {item[axis] for item in group} != {recipe[axis] for recipe in group_recipes}:
                    fail('coverage', f'Supported font/weight/modifier lacks catalog {axis} levels', group[0]['taskId'])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        fail('census', f'Complete frozen catalog and skipped-candidate census required: {error}')

    pixel_hashes = {}
    checked_assets = {}
    prompts = {item.get('prompt') for item in items if isinstance(item.get('prompt'), str)}
    for item in items:
        task_id = item['taskId']
        prompt = item.get('prompt')
        if not isinstance(prompt, str) or not prompt.strip() or len(prompts) != 1 or prompt != catalog.get('prompt'):
            fail('prompt', 'All tasks must use the shared frozen catalog prompt', task_id)
        if not item.get('pangram') or item.get('pangram') != catalog.get('pangram'):
            fail('text', 'Text must equal the shared frozen pangram', task_id)
        if item.get('weightNumeric') != WEIGHTS[item['weight']] or item.get('widthPx') != WIDTHS.get(str(item.get('widthId'))):
            fail('labels', 'Numeric weight or width disagrees with label', task_id)
        dimensions = None
        ink = None
        try:
            file = _local_file(root, item.get('imageFilename'))
            if hashlib.sha256(file.read_bytes()).hexdigest() != item.get('imageSha256'):
                fail('image_hash', 'Missing or mismatched PNG SHA256', task_id)
            with Image.open(file) as image:
                if image.format != 'PNG':
                    raise ValueError('Expected PNG image')
                image.verify()
            with Image.open(file) as image:
                rgba = image.convert('RGBA')
                if rgba.getextrema()[3][0] != 255:
                    raise ValueError('Transparent sample pixels are not allowed')
                rgb = rgba.convert('RGB')
                dimensions = image.size
                channels = [channel.point(lambda value: 255 if value < 160 else 0) for channel in rgb.split()]
                ink = ImageChops.multiply(ImageChops.multiply(channels[0], channels[1]), channels[2])
                box = ink.getbbox()
                if box is None:
                    raise ValueError('No visible dark text')
                if box[0] < 2 or box[1] < 2 or box[2] > image.width - 2 or box[3] > image.height - 2:
                    raise ValueError('Text reaches the image edge; possible clipping')
                pixel_hash = hashlib.sha256(str(dimensions).encode() + rgb.tobytes()).hexdigest()
                if pixel_hash in pixel_hashes:
                    fail('duplicate_pixels', f'Identical pixels also used by {pixel_hashes[pixel_hash]}', task_id)
                pixel_hashes[pixel_hash] = task_id
        except (OSError, ValueError, TypeError, KeyError) as error:
            fail('image', str(error), task_id)

        try:
            layout = item['layout']
            count, boxes = layout['lineCount'], layout['lineBoxes']
            if not isinstance(count, int) or isinstance(count, bool) or count < 2 or len(boxes) != count:
                raise ValueError('At least two measured text lines are required')
            for key in ('contentWidthPx', 'cardWidthPx', 'cardHeightPx', 'fontSizePx', 'lineHeightPx'):
                if not _number(layout[key]) or layout[key] <= 0:
                    raise ValueError(f'Invalid layout {key}')
            if layout['fontSizePx'] != 22 or abs(layout['lineHeightPx'] - 22 * LINE_HEIGHTS[item['lineHeight']]) > 0.1:
                raise ValueError('Measured font size or line height disagrees with CSS label')
            if layout.get('deviceScaleFactor') != 2 or not _number(layout.get('letterSpacingPx')) or abs(layout['letterSpacingPx'] - TRACKING[item['kerning']]) > 0.01:
                raise ValueError('Measured pixel scale or tracking disagrees with label')
            if layout['cardWidthPx'] != item['widthPx'] or abs(layout['contentWidthPx'] - (item['widthPx'] - 50)) > 0.1:
                raise ValueError('Measured card width or content area disagrees with width label')
            if dimensions and any(abs(measured * 2 - actual) > 2 for measured, actual in zip(
                    (layout['cardWidthPx'], layout['cardHeightPx']), dimensions)):
                raise ValueError('PNG dimensions disagree with measured card at 2× scale')
            for index, box in enumerate(boxes):
                if not all(_number(box[key]) for key in ('x', 'y', 'width', 'height')):
                    raise ValueError('Non-numeric line bounds')
                if box['x'] < 0 or box['y'] < 0 or box['width'] <= 0 or box['height'] <= 0 or box['x'] + box['width'] > layout['cardWidthPx'] + 1 or box['y'] + box['height'] > layout['cardHeightPx'] + 1:
                    raise ValueError('Text line extends outside card')
                if index and abs(box['y'] - boxes[index - 1]['y'] - layout['lineHeightPx']) > 0.2:
                    raise ValueError('Measured line separation disagrees with line-height label')
                if ink is not None:
                    # Previous-line descenders cannot prove that another line exists.
                    top = max(box['y'], boxes[index - 1]['y'] + boxes[index - 1]['height']) if index else box['y']
                    bottom = box['y'] + box['height']
                    pixel_box = (math.floor(box['x'] * 2), math.ceil(top * 2),
                                 math.ceil((box['x'] + box['width']) * 2), math.floor(bottom * 2))
                    if bottom <= top or ink.crop(pixel_box).getbbox() is None:
                        raise ValueError(f'Measured text line {index + 1} has no visible ink')
        except (KeyError, ValueError, TypeError, IndexError, AttributeError) as error:
            fail('layout', f'Missing or invalid layout evidence: {error}', task_id)

        try:
            evidence = item['fontRendering']
            assets = evidence['assets']
            faces = evidence['platformFonts']
            loaded = evidence['loadedFaces']
            if not evidence.get('browserVersion') or evidence.get('syntheticItalic') is not False:
                raise ValueError('Browser identity and non-synthetic font evidence required')
            if not assets or not faces or not loaded or any(face.get('isCustomFont') is not True or face.get('glyphCount', 0) <= 0 for face in faces):
                raise ValueError('Every glyph must use an identified downloaded font')
            if evidence.get('smallCapsSynthesisAllowed') is not (item['modifier'] == 'small-caps'):
                raise ValueError('Small-caps synthesis policy disagrees with modifier')
            for face in loaded:
                weights = [float(value) for value in face['weight'].split()]
                if not weights[0] <= WEIGHTS[item['weight']] <= weights[-1]:
                    raise ValueError('Loaded CSS weight does not support label')
                if (face['style'] == 'italic') != (item['modifier'] == 'italic'):
                    raise ValueError('Loaded style disagrees with modifier')
            for face in faces:
                matching = [asset for asset in assets if asset.get('postscriptName') == face.get('postScriptName')]
                if not matching:
                    raise ValueError('Actual browser face has no frozen binary evidence')
                if not any((asset.get('italic') is (item['modifier'] == 'italic')) and
                           asset.get('weightRange', [asset.get('weight', 0)] * 2)[0] <= WEIGHTS[item['weight']] <=
                           asset.get('weightRange', [asset.get('weight', 0)] * 2)[-1] for asset in matching):
                    raise ValueError('Font binary weight/style disagrees with target')
            for asset in assets:
                try:
                    file = _local_file(root, asset['path'])
                    if file not in checked_assets:
                        checked_assets[file] = _font_metadata(file.read_bytes())
                    actual = checked_assets[file]
                    if any(asset.get(key) != value for key, value in actual.items()):
                        raise ValueError('Frozen font metadata differs from the actual binary')
                    expected_names = [item['fontName'], *fonts.get(item.get('fontId'), {}).get('binaryFamilyNames', [])]
                    identities = [actual['familyName'], actual['typographicFamily']]
                    if not {_normalize(name) for name in expected_names} & {_normalize(name) for name in identities}:
                        raise ValueError('Internal font family differs from the target family')
                except (KeyError, ValueError, TypeError, OSError, AttributeError) as error:
                    fail('font_asset', str(error), task_id)
        except (KeyError, ValueError, TypeError, IndexError, AttributeError) as error:
            fail('font_provenance', f'Missing or invalid font evidence: {error}', task_id)

    report['valid'] = not report['errors']
    report['unique_pixel_count'] = len(pixel_hashes)
    report['font_asset_count'] = len(checked_assets)
    report['error_counts'] = dict(Counter(error['code'] for error in report['errors']))
    return report


def require_valid_dataset(manifest_path: str | Path) -> dict:
    report = validate_dataset(manifest_path)
    if not report['valid']:
        first = report['errors'][0]
        raise ValueError(f"Dataset validation failed ({len(report['errors'])} findings): {first['code']}: {first['detail']}. Run python -m baseline.validate_dataset for the complete report; regenerate historical inputs.")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', help='Write complete JSON evidence to this file')
    args = parser.parse_args()
    report = validate_dataset(args.manifest)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + '\n')
    summary = {key: value for key, value in report.items() if key != 'errors'}
    print(json.dumps(summary, indent=2))
    if report['errors']:
        print(json.dumps(report['errors'][:5], indent=2))
    raise SystemExit(0 if report['valid'] else 1)


if __name__ == '__main__':
    main()
