import { afterEach, beforeEach, expect, test } from 'bun:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { buildHarborDataset } from './generate_harbor_dataset';
import type { RenderedSampleMeta } from './render';

let root: string;
let rendered: string;
let output: string;
const sample: RenderedSampleMeta = {
  taskId: 'font-secret-v01', fontId: 'secret', fontName: 'Secret Face',
  aliases: ['Secret MT'], category: 'non-serif', weight: 'bold', weightNumeric: 700,
  modifier: 'italic', kerning: 'tight', lineHeight: 'loose', widthId: 'narrow', widthPx: 220,
  imageFilename: 'sample.png', imagePath: 'sample.png', pangram: 'A test pangram.', prompt: 'Identify it.',
};
const answer = {
  font: sample.fontName, category: sample.category, weight: sample.weight,
  modifier: sample.modifier, kerning: sample.kerning, line_height: sample.lineHeight,
};

beforeEach(() => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), 'fontbench-harbor-test-'));
  rendered = path.join(root, 'rendered');
  output = path.join(root, 'dataset');
  fs.mkdirSync(rendered);
  fs.writeFileSync(path.join(rendered, 'sample.png'), 'fixture image');
  writeManifest([sample]);
});
afterEach(() => fs.rmSync(root, { recursive: true, force: true }));

function writeManifest(samples: unknown) {
  fs.writeFileSync(path.join(rendered, 'manifest.json'), JSON.stringify(samples));
}

function verify(data: unknown, cwd = path.join(output, 'tasks', sample.taskId, 'tests')) {
  const taskDir = path.join(output, 'tasks', sample.taskId);
  fs.writeFileSync(path.join(cwd, 'output.json'), typeof data === 'string' ? data : JSON.stringify(data));
  const logsDir = path.join(root, 'logs');
  const result = spawnSync('bash', [path.join(taskDir, 'tests', 'test.sh')], {
    cwd, encoding: 'utf8', env: { ...process.env, HARBOR_LOGS_DIR: logsDir },
  });
  const reward = path.join(logsDir, 'reward.txt');
  expect(fs.existsSync(reward), result.stderr).toBe(true);
  return { score: Number(fs.readFileSync(reward, 'utf8')), status: result.status };
}

test('instructions are independent of hidden typography answers', () => {
  buildHarborDataset(rendered, output);
  const first = fs.readFileSync(path.join(output, 'tasks', sample.taskId, 'instruction.md'), 'utf8');
  writeManifest([{ ...sample, fontName: 'Another Secret', weight: 'thin', modifier: 'underline' }]);
  buildHarborDataset(rendered, output);
  const second = fs.readFileSync(path.join(output, 'tasks', sample.taskId, 'instruction.md'), 'utf8');
  expect(first).toBe(second);
  expect(first).not.toContain(sample.fontName);
});

test.each([
  {}, [], null, 'not JSON',
  { font: 'S', category: 'serif', weight: 'b', modifier: 'i', kerning: 't', line_height: 'l' },
  { font: ['Secret Face'], category: ['non-serif'], weight: true, modifier: false, kerning: null, line_height: 1 },
].map(data => [data]))(
  'invalid or partial-name response %j earns zero', (data) => {
    buildHarborDataset(rendered, output);
    expect(verify(data).score).toBe(0);
  },
);

test('verifier reads ground truth relative to its script, independent of working directory', () => {
  buildHarborDataset(rendered, output);
  expect(verify(answer, root).score).toBe(1);
});

test('font aliases and exact categories pass, partial answers retain only their earned credit', () => {
  buildHarborDataset(rendered, output);
  expect(verify({ ...answer, font: ' SECRET-mt ', category: ' NON-SERIF ' }).score).toBe(1);
  expect(verify({ font: sample.fontName }).score).toBeCloseTo(1 / 6, 6);
  expect(verify({ ...answer, font: 'Secret Face Mono' }).score).toBeCloseTo(5 / 6, 6);
});

test('missing output earns zero and verification completes successfully', () => {
  buildHarborDataset(rendered, output);
  const testsDir = path.join(output, 'tasks', sample.taskId, 'tests');
  const logsDir = path.join(root, 'logs');
  const result = spawnSync('bash', [path.join(testsDir, 'test.sh')], {
    cwd: root, encoding: 'utf8', env: { ...process.env, HARBOR_LOGS_DIR: logsDir },
  });
  expect(result.status, result.stderr).toBe(0);
  expect(Number(fs.readFileSync(path.join(logsDir, 'reward.txt'), 'utf8'))).toBe(0);
});

test('oracle JSON escapes arbitrary font names', () => {
  writeManifest([{ ...sample, fontName: 'Secret "Face"\\Variant\nEOF' }]);
  buildHarborDataset(rendered, output);
  const script = fs.readFileSync(path.join(output, 'tasks', sample.taskId, 'solution', 'solve.sh'), 'utf8');
  const json = script.split('cat << \'EOF\' > "$target"\n')[1]!.split('\nEOF')[0]!;
  expect(JSON.parse(json).font).toBe('Secret "Face"\\Variant\nEOF');
});

test('missing images reject generation before modifying a previous dataset', () => {
  buildHarborDataset(rendered, output);
  const previous = fs.readFileSync(path.join(output, 'dataset.toml'), 'utf8');
  writeManifest([sample, { ...sample, taskId: 'missing', imageFilename: 'missing.png' }]);
  expect(() => buildHarborDataset(rendered, output)).toThrow(/image|ENOENT/i);
  expect(fs.readFileSync(path.join(output, 'dataset.toml'), 'utf8')).toBe(previous);
  expect(fs.existsSync(path.join(output, 'tasks', 'missing'))).toBe(false);
});

test.each([
  [{ ...sample, taskId: '../../escaped' }],
  [sample, sample],
  [{ ...sample, imageFilename: '../outside.png' }],
  [{ ...sample, category: 'invalid' }],
].map(samples => [samples]))('invalid manifest records are rejected before writing tasks', (samples) => {
  fs.writeFileSync(path.join(root, 'outside.png'), 'outside');
  writeManifest(samples);
  expect(() => buildHarborDataset(rendered, output)).toThrow();
  expect(fs.existsSync(path.join(output, 'tasks'))).toBe(false);
});

test('regeneration removes obsolete generated tasks', () => {
  writeManifest([sample, { ...sample, taskId: 'obsolete' }]);
  buildHarborDataset(rendered, output);
  writeManifest([sample]);
  buildHarborDataset(rendered, output);
  expect(fs.readdirSync(path.join(output, 'tasks'))).toEqual([sample.taskId]);
});

test('regeneration preserves extra files in obsolete tasks and reports the conflict', () => {
  writeManifest([sample, { ...sample, taskId: 'obsolete' }]);
  buildHarborDataset(rendered, output);
  const notes = path.join(output, 'tasks', 'obsolete', 'notes.md');
  fs.writeFileSync(notes, 'User notes');
  writeManifest([sample]);
  expect(() => buildHarborDataset(rendered, output)).toThrow(/unrecognized stale task/);
  expect(fs.readFileSync(notes, 'utf8')).toBe('User notes');
});

test('image symlinks cannot read files outside the rendering directory', () => {
  fs.writeFileSync(path.join(root, 'outside.png'), 'outside');
  fs.symlinkSync(path.join(root, 'outside.png'), path.join(rendered, 'link.png'));
  writeManifest([{ ...sample, imageFilename: 'link.png' }]);
  expect(() => buildHarborDataset(rendered, output)).toThrow(/inside/);
  expect(fs.existsSync(output)).toBe(false);
});
