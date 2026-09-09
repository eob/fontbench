import { afterEach, beforeEach, expect, test } from 'bun:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { assertMutableOutput } from './release_protection';

let repository: string;
const release = { dataset_manifest: 'frozen/rendered/manifest.json', harbor_dataset: 'frozen/harbor' };

beforeEach(() => {
  repository = fs.mkdtempSync(path.join(os.tmpdir(), 'fontbench-release-test-'));
  for (const directory of ['releases', 'frozen/rendered', 'frozen/harbor']) {
    fs.mkdirSync(path.join(repository, directory), { recursive: true });
  }
  fs.writeFileSync(path.join(repository, 'releases/1.0.0.json'), JSON.stringify(release));
});
afterEach(() => fs.rmSync(repository, { recursive: true, force: true }));

test.each(['frozen/rendered', 'frozen/rendered/new/subdirectory', 'frozen/harbor', 'frozen/harbor/tasks/new', 'frozen', '.', '/'])(
  'refuses an overlapping registered output: %s', directory => {
    expect(() => assertMutableOutput(path.resolve(repository, directory), repository)).toThrow(/Frozen release output/);
  },
);

test.each(['candidate-rendered', 'frozen/rendered-copy', 'frozen/harbor-next', 'new/parent/candidate'])(
  'permits a separate output without creating it: %s', directory => {
    const output = path.join(repository, directory);
    expect(() => assertMutableOutput(output, repository)).not.toThrow();
    expect(fs.existsSync(output)).toBe(false);
  },
);

test('refuses aliases through existing symlink parents', () => {
  fs.symlinkSync(path.join(repository, 'frozen'), path.join(repository, 'alias'));
  expect(() => assertMutableOutput(path.join(repository, 'alias/rendered'), repository)).toThrow(/Frozen release output/);
  expect(() => assertMutableOutput(path.join(repository, 'alias/harbor/new/child'), repository)).toThrow(/Frozen release output/);
});

test('rejects dangling symlinks instead of treating them as new output directories', () => {
  fs.symlinkSync(path.join(repository, 'frozen/rendered/missing'), path.join(repository, 'alias'));
  expect(() => assertMutableOutput(path.join(repository, 'alias/child'), repository)).toThrow(/Cannot resolve output symlink/);
});

test.each([null, [], {}, { dataset_manifest: release.dataset_manifest }, { ...release, harbor_dataset: '../outside' },
  { ...release, harbor_dataset: '/outside' }, { ...release, harbor_dataset: 'frozen\\harbor' }, { ...release, harbor_dataset: '' }].map(entry => ({ entry })))(
  'refuses malformed registry declarations: %j', ({ entry }) => {
    fs.writeFileSync(path.join(repository, 'releases/1.0.0.json'), JSON.stringify(entry));
    expect(() => assertMutableOutput(path.join(repository, 'candidate'), repository)).toThrow(/Invalid .*release registry/);
  },
);

test('does not ignore malformed JSON in another registered release', () => {
  fs.writeFileSync(path.join(repository, 'releases/2.0.0.json'), '{');
  expect(() => assertMutableOutput(path.join(repository, 'candidate'), repository)).toThrow();
});

test('does not proceed when the release registry is missing', () => {
  fs.rmSync(path.join(repository, 'releases'), { recursive: true });
  expect(() => assertMutableOutput(path.join(repository, 'candidate'), repository)).toThrow();
});
