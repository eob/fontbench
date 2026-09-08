import { afterEach, beforeEach, expect, test } from 'bun:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
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
  imageFilename: 'sample.png', imagePath: 'sample.png', pangram: 'A test pangram.', prompt: fs.readFileSync(path.join(import.meta.dir, '../baseline/prompt.txt'), 'utf8').trim(),
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
  fs.writeFileSync(path.join(rendered, 'sample.png'), Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP8//8/AwMDEwMDAwMDAwAkBgMB/DXemwAAAABJRU5ErkJggg==', 'base64'));
  writeManifest([sample]);
});
afterEach(() => fs.rmSync(root, { recursive: true, force: true }));

function writeManifest(samples: unknown) {
  fs.writeFileSync(path.join(rendered, 'manifest.json'), JSON.stringify(samples));
}

function harborId() {
  return 'task-' + createHash('sha256').update(fs.readFileSync(path.join(rendered, 'sample.png'))).update(sample.taskId).digest('hex').slice(0, 24);
}

function verify(data: unknown, cwd?: string) {
  const taskDir = path.join(output, 'tasks', harborId());
  cwd ??= path.join(taskDir, 'tests');
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
  const first = fs.readFileSync(path.join(output, 'tasks', harborId(), 'instruction.md'), 'utf8');
  writeManifest([{ ...sample, fontName: 'Another Secret', weight: 'thin', modifier: 'underline' }]);
  buildHarborDataset(rendered, output);
  const second = fs.readFileSync(path.join(output, 'tasks', harborId(), 'instruction.md'), 'utf8');
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

test('font aliases pass and incomplete answers receive zero credit', () => {
  buildHarborDataset(rendered, output);
  expect(verify({ ...answer, font: ' SECRET-mt ', category: ' NON-SERIF ' }).score).toBe(1);
  expect(verify({ font: sample.fontName }).score).toBe(0);
  expect(verify({ ...answer, font: 'Secret Face Mono' }).score).toBeCloseTo(5 / 6, 6);
});

test('missing output earns zero and verification completes successfully', () => {
  buildHarborDataset(rendered, output);
  const testsDir = path.join(output, 'tasks', harborId(), 'tests');
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
  const script = fs.readFileSync(path.join(output, 'tasks', harborId(), 'solution', 'solve.sh'), 'utf8');
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
  expect(fs.readdirSync(path.join(output, 'tasks'))).toEqual([harborId()]);
});

test('regeneration preserves extra files in obsolete tasks and reports the conflict', () => {
  writeManifest([sample, { ...sample, taskId: 'obsolete' }]);
  buildHarborDataset(rendered, output);
  const obsolete = fs.readdirSync(path.join(output, 'tasks')).find(id => id !== harborId())!;
  const notes = path.join(output, 'tasks', obsolete, 'notes.md');
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


test('public task metadata contains no hidden labels or source IDs', () => {
  buildHarborDataset(rendered, output);
  const taskDir = path.join(output, 'tasks', harborId());
  expect(fs.existsSync(taskDir)).toBe(true);
  const toml = fs.readFileSync(path.join(taskDir, 'task.toml'), 'utf8');
  for (const secret of [sample.taskId, sample.fontName, sample.category, sample.weight, sample.modifier, sample.widthId]) {
    expect(toml).not.toContain(secret);
  }
});

test('corrupt PNG bytes are rejected before creating or replacing a package', () => {
  fs.writeFileSync(path.join(rendered, 'sample.png'), 'not a PNG');
  expect(() => buildHarborDataset(rendered, output)).toThrow(/PNG/);
  expect(fs.existsSync(output)).toBe(false);
});

test('retained task environment extras cannot enter a regenerated benchmark', () => {
  buildHarborDataset(rendered, output);
  const note = path.join(output, 'tasks', harborId(), 'environment', 'answers.json');
  fs.writeFileSync(note, 'private user data');
  expect(() => buildHarborDataset(rendered, output)).toThrow(/unrecognized/);
  expect(fs.readFileSync(note, 'utf8')).toBe('private user data');
});

test.each([
  { ...answer, unexpected: 'field' },
  { ...answer, font: '   ' },
  { ...answer, weight: 'B' },
  JSON.stringify(answer).replace('"font":', '"font":"wrong","font":'),
])('invalid complete response %j receives zero total credit', data => {
  buildHarborDataset(rendered, output);
  expect(verify(data).score).toBe(0);
});

test('PNG corruption and mismatched provenance are rejected', () => {
  const bytes = fs.readFileSync(path.join(rendered, 'sample.png'));
  bytes[45] = bytes[45]! ^ 1;
  fs.writeFileSync(path.join(rendered, 'sample.png'), bytes);
  expect(() => buildHarborDataset(rendered, output)).toThrow(/PNG/);
});

test('an existing package survives a failed staging write', () => {
  buildHarborDataset(rendered, output);
  const before = fs.readFileSync(path.join(output, 'dataset.toml'));
  const original = fs.writeFileSync;
  fs.writeFileSync = ((...args: Parameters<typeof fs.writeFileSync>) => {
    if (String(args[0]).endsWith('instruction.md')) throw new Error('simulated write failure');
    return original(...args);
  }) as typeof fs.writeFileSync;
  try {
    expect(() => buildHarborDataset(rendered, output)).toThrow('simulated write failure');
  } finally { fs.writeFileSync = original; }
  expect(fs.readFileSync(path.join(output, 'dataset.toml'))).toEqual(before);
  expect(fs.existsSync(path.join(output, 'tasks', harborId(), 'instruction.md'))).toBe(true);
});

test('retained environment symlinks cannot redirect package writes', () => {
  buildHarborDataset(rendered, output);
  const environment = path.join(output, 'tasks', harborId(), 'environment');
  fs.renameSync(environment, path.join(root, 'external'));
  fs.symlinkSync(path.join(root, 'external'), environment);
  expect(() => buildHarborDataset(rendered, output)).toThrow(/unrecognized/);
  expect(fs.existsSync(path.join(root, 'external', 'sample.png'))).toBe(true);
});


test('packaged instructions use the exact shared prompt', () => {
  buildHarborDataset(rendered, output);
  const instruction = fs.readFileSync(path.join(output, 'tasks', harborId(), 'instruction.md'), 'utf8');
  expect(instruction.startsWith(sample.prompt)).toBe(true);
  writeManifest([{ ...sample, prompt: 'The answer is secret.' }]);
  expect(() => buildHarborDataset(rendered, output)).toThrow(/Prompt differs/);
});
