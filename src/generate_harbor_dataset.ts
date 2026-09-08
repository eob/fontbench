import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { crc32, inflateSync } from 'node:zlib';
import type { RenderedSampleMeta } from './render';

function validatePng(bytes: Buffer, filename: string) {
  const invalid = () => new Error(`Invalid PNG benchmark image: ${filename}`);
  if (!bytes.subarray(0, 8).equals(Buffer.from('89504e470d0a1a0a', 'hex'))) throw invalid();
  let offset = 8;
  let width = 0;
  let height = 0;
  let channels = 0;
  let ended = false;
  const compressed: Buffer[] = [];
  while (offset + 12 <= bytes.length) {
    const length = bytes.readUInt32BE(offset);
    const end = offset + 8 + length;
    if (end + 4 > bytes.length) throw invalid();
    const type = bytes.toString('ascii', offset + 4, offset + 8);
    const data = bytes.subarray(offset + 8, end);
    if (crc32(bytes.subarray(offset + 4, end)) !== bytes.readUInt32BE(end)) throw invalid();
    if (offset === 8 && type !== 'IHDR') throw invalid();
    if (type === 'IHDR') {
      if (offset !== 8 || length !== 13) throw invalid();
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      channels = data[9] === 2 ? 3 : data[9] === 6 ? 4 : 0;
      // Chromium screenshots use non-interlaced, eight-bit RGB or RGBA PNGs.
      if (!width || !height || !channels || data[8] !== 8 || data[10] || data[11] || data[12]) throw invalid();
    } else if (type === 'IDAT') compressed.push(data);
    else if (type === 'IEND') {
      if (length || end + 4 !== bytes.length) throw invalid();
      ended = true;
      break;
    } else if (type[0] === type[0]?.toUpperCase()) throw invalid();
    offset = end + 4;
  }
  const stride = width * channels + 1;
  const expected = stride * height;
  if (!ended || !compressed.length || expected > 64 * 1024 * 1024) throw invalid();
  let pixels: Buffer;
  try { pixels = inflateSync(Buffer.concat(compressed), { maxOutputLength: expected }); }
  catch { throw invalid(); }
  if (pixels.length !== expected) throw invalid();
  for (let row = 0; row < height; row++) if (pixels[row * stride]! > 4) throw invalid();
}

export function buildHarborDataset(
  renderedDir: string = 'dataset/fontbench-2-rendered',
  outputDir: string = 'dataset/fontbench-2'
) {
  const prompt = fs.readFileSync(path.join(import.meta.dir, '../baseline/prompt.txt'), 'utf8').trim();
  const manifestPath = path.join(renderedDir, 'manifest.json');
  if (!fs.existsSync(manifestPath)) {
    throw new Error(`Manifest not found at ${manifestPath}. Run rendering first.`);
  }

  const manifest: RenderedSampleMeta[] = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
  if (!Array.isArray(manifest) || !manifest.length) throw new Error('Manifest must contain a non-empty array of samples.');
  const inputs = new Map<string, { bytes: Buffer; harborId: string }>();
  const taskIds = new Set<string>();
  const renderedRoot = fs.realpathSync(renderedDir);
  const enumValues = {
    category: ['serif', 'non-serif', 'mono', 'handwriting', 'other'],
    weight: ['thin', 'regular', 'bold', 'black'],
    modifier: ['regular', 'italic', 'underline', 'strikethrough', 'small-caps'],
    kerning: ['tight', 'normal', 'loose'],
    lineHeight: ['tight', 'normal', 'loose'],
    widthId: ['narrow', 'medium', 'wide'],
  };
  // Validate every input before modifying a previously generated dataset.
  for (const sample of manifest) {
    if (!sample || typeof sample.taskId !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(sample.taskId)) {
      throw new Error('Invalid task ID in manifest.');
    }
    if (taskIds.has(sample.taskId)) throw new Error(`Duplicate task ID: ${sample.taskId}`);
    taskIds.add(sample.taskId);
    for (const key of Object.keys(enumValues) as (keyof typeof enumValues)[]) {
      if (!enumValues[key].includes(sample[key])) throw new Error(`Invalid ${key} for ${sample.taskId}`);
    }
    if (sample.prompt !== prompt) throw new Error(`Prompt differs from the shared evaluation protocol: ${sample.taskId}`);
    if (typeof sample.fontName !== 'string' || !sample.fontName.trim()
      || typeof sample.pangram !== 'string'
      || !Array.isArray(sample.aliases) || sample.aliases.some(alias => typeof alias !== 'string')
      || !Number.isFinite(sample.widthPx) || sample.widthPx <= 0) {
      throw new Error(`Invalid sample metadata for ${sample.taskId}`);
    }
    if (typeof sample.imageFilename !== 'string' || path.isAbsolute(sample.imageFilename)) {
      throw new Error(`Invalid image filename for ${sample.taskId}`);
    }
    const imagePath = fs.realpathSync(path.join(renderedRoot, sample.imageFilename));
    if (!imagePath.startsWith(renderedRoot + path.sep) || !fs.statSync(imagePath).isFile()) {
      throw new Error(`Image must be a file inside ${renderedDir}: ${sample.imageFilename}`);
    }
    const bytes = fs.readFileSync(imagePath);
    validatePng(bytes, sample.imageFilename);
    const digest = createHash('sha256').update(bytes).digest('hex');
    if ('imageSha256' in sample && sample.imageSha256 !== digest) throw new Error(`Image checksum mismatch: ${sample.taskId}`);
    const harborId = 'task-' + createHash('sha256').update(bytes).update(sample.taskId).digest('hex').slice(0, 24);
    inputs.set(sample.taskId, { bytes, harborId });
  }
  const previousTasksDir = path.join(outputDir, 'tasks');
  if (fs.existsSync(outputDir)) {
    if (fs.lstatSync(outputDir).isSymbolicLink()) throw new Error('Output directory cannot be a symlink');
    const topEntries = fs.readdirSync(outputDir);
    if (topEntries.some(name => !['dataset.toml', 'tasks'].includes(name))) throw new Error(`Unrecognized dataset output: ${outputDir}`);
    if (fs.existsSync(path.join(outputDir, 'dataset.toml')) && !fs.lstatSync(path.join(outputDir, 'dataset.toml')).isFile()) {
      throw new Error('Dataset descriptor must be a regular file');
    }
  }
  if (fs.existsSync(previousTasksDir)) {
    if (fs.lstatSync(previousTasksDir).isSymbolicLink()) throw new Error(`Task directory cannot be a symlink: ${previousTasksDir}`);
    for (const entry of fs.readdirSync(previousTasksDir, { withFileTypes: true })) {
      const taskDir = path.join(previousTasksDir, entry.name);
      if (!entry.isDirectory()) throw new Error(`Unexpected task entry: ${taskDir}`);
      const expectedFiles = [
        'task.toml', 'instruction.md', 'environment', 'environment/Dockerfile', 'environment/sample.png',
        'solution', 'solution/solve.sh', 'tests', 'tests/test.sh', 'tests/ground_truth.json',
      ];
      const entries = fs.readdirSync(taskDir, { recursive: true, encoding: 'utf8' });
      if (entries.length !== expectedFiles.length || entries.some(file => !expectedFiles.includes(file)
        || fs.lstatSync(path.join(taskDir, file)).isSymbolicLink())) {
        throw new Error(`Refusing to replace unrecognized stale task directory: ${taskDir}`);
      }
      const truth = JSON.parse(fs.readFileSync(path.join(taskDir, 'tests', 'ground_truth.json'), 'utf8'));
      if ((truth.harborTaskId ?? truth.taskId) !== entry.name) throw new Error(`Unrecognized task identity: ${taskDir}`);
    }
  }
  const destination = path.resolve(outputDir);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  const transaction = fs.mkdtempSync(path.join(path.dirname(destination), '.fontbench-package-'));
  const stagingDir = path.join(transaction, 'new');
  const backupDir = path.join(transaction, 'previous');
  const tasksDir = path.join(stagingDir, 'tasks');
  fs.mkdirSync(tasksDir, { recursive: true });
  try {
  console.log(`Generating Harbor dataset at ${outputDir} for ${manifest.length} tasks...`);

  const datasetToml = `version = "1.0"

[dataset]
name = "fontbench-2"
version = "2.0.0"
description = "FontBench-2: Visual typography benchmark across six attributes: font, category, weight, modifier, kerning, and line height."
author = "Edward Benson"
license = "MIT"
task_dir = "tasks"

[metadata]
grading_version = "3"
total_tasks = ${manifest.length}
primary_pangram = "The quick brown fox jumps over the lazy dog."
`;
  fs.writeFileSync(path.join(stagingDir, 'dataset.toml'), datasetToml, 'utf-8');

  for (const sample of manifest) {
    const { bytes, harborId } = inputs.get(sample.taskId)!;
    const taskDir = path.join(tasksDir, harborId);
    const envDir = path.join(taskDir, 'environment');
    const solDir = path.join(taskDir, 'solution');
    const testsDir = path.join(taskDir, 'tests');

    fs.mkdirSync(envDir, { recursive: true });
    fs.mkdirSync(solDir, { recursive: true });
    fs.mkdirSync(testsDir, { recursive: true });

    fs.writeFileSync(path.join(envDir, 'sample.png'), bytes);

    const taskToml = `version = "1.0"

[metadata]
name = "${harborId}"
author_name = "Edward Benson"
difficulty = "medium"
category = "vision"
tags = ["typography", "font-identification", "vlm"]

[agent]
timeout_sec = 180.0

[verifier]
timeout_sec = 60.0
`;
    fs.writeFileSync(path.join(taskDir, 'task.toml'), taskToml, 'utf-8');

    const instructionMd = `${prompt}

Examine the rendered image at \`/workspace/sample.png\`.
Write your JSON object into \`/workspace/output.json\`.
`;
    fs.writeFileSync(path.join(taskDir, 'instruction.md'), instructionMd, 'utf-8');

    const dockerfile = `FROM alpine:3.24
RUN apk add --no-cache bash python3
WORKDIR /workspace
COPY sample.png /workspace/sample.png
`;
    fs.writeFileSync(path.join(envDir, 'Dockerfile'), dockerfile, 'utf-8');

    const solveSh = `#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
${JSON.stringify({
  font: sample.fontName, category: sample.category, weight: sample.weight,
  modifier: sample.modifier, kerning: sample.kerning, line_height: sample.lineHeight,
}, null, 2)}
EOF
`;
    const solvePath = path.join(solDir, 'solve.sh');
    fs.writeFileSync(solvePath, solveSh, 'utf-8');
    fs.chmodSync(solvePath, 0o755);

    const groundTruth = {
      taskId: sample.taskId,
      harborTaskId: harborId,
      canonical: sample.fontName,
      aliases: sample.aliases,
      category: sample.category,
      weight: sample.weight,
      modifier: sample.modifier,
      kerning: sample.kerning,
      lineHeight: sample.lineHeight,
      widthId: sample.widthId,
      widthPx: sample.widthPx
    };
    fs.writeFileSync(path.join(testsDir, 'ground_truth.json'), JSON.stringify(groundTruth, null, 2), 'utf-8');

    const testSh = `#!/bin/bash
set -euo pipefail

python3 - "$(dirname -- "\${BASH_SOURCE[0]}")/ground_truth.json" <<'PY_GRADER'
import json, os, re, sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    gt = json.load(f)

def normalize(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', text.lower())

candidate_paths = [
    "/workspace/output.json",
    "./output.json"
]

def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Duplicate JSON key")
        obj[key] = value
    return obj

allowed = {
    "category": ["serif", "non-serif", "mono", "handwriting", "other"],
    "weight": ["thin", "regular", "bold", "black"],
    "modifier": ["regular", "italic", "underline", "strikethrough", "small-caps"],
    "kerning": ["tight", "normal", "loose"],
    "line_height": ["tight", "normal", "loose"],
}

data = {}
for p in candidate_paths:
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                value = json.load(f, object_pairs_hook=unique_object)
                if (isinstance(value, dict) and set(value) == {"font", *allowed}
                        and all(isinstance(v, str) for v in value.values())
                        and value["font"].strip()
                        and all(value[key].strip().lower() in choices for key, choices in allowed.items())):
                    data = value
        except (OSError, ValueError):
            pass
        break

font = data.get("font", "")
pred_font = normalize(font) if isinstance(font, str) else ""
accepted_names = [gt["canonical"]] + gt.get("aliases", [])
accepted_norms = [normalize(a) for a in accepted_names if a]
font_pass = bool(pred_font) and pred_font in accepted_norms

def matches(key, expected):
    value = data.get(key)
    return isinstance(value, str) and value.strip().lower() == expected

cat_pass = matches("category", gt["category"])
weight_pass = matches("weight", gt["weight"])
mod_pass = matches("modifier", gt["modifier"])
kern_pass = matches("kerning", gt["kerning"])
lh_pass = matches("line_height", gt["lineHeight"])

score = sum([font_pass, cat_pass, weight_pass, mod_pass, kern_pass, lh_pass]) / 6.0

logs_dir = os.environ.get("HARBOR_LOGS_DIR", "")
if not logs_dir:
    logs_dir = "/logs/verifier" if os.path.exists("/logs") and os.access("/logs", os.W_OK) else "./logs/verifier"

os.makedirs(logs_dir, exist_ok=True)
reward_path = os.path.join(logs_dir, "reward.txt")
with open(reward_path, "w", encoding="utf-8") as f:
    f.write(f"{score}\\n")

print(f"[FontBench-2 Verifier] Task: {gt['taskId']} - Score: {score*100:.1f}%")
print(f"  Font: {'PASS' if font_pass else 'FAIL'} | Cat: {'PASS' if cat_pass else 'FAIL'} | Weight: {'PASS' if weight_pass else 'FAIL'}")
PY_GRADER
`;
    const testPath = path.join(testsDir, 'test.sh');
    fs.writeFileSync(testPath, testSh, 'utf-8');
    fs.chmodSync(testPath, 0o755);
  }

  if (fs.existsSync(destination)) fs.renameSync(destination, backupDir);
  try { fs.renameSync(stagingDir, destination); }
  catch (error) {
    if (fs.existsSync(backupDir)) fs.renameSync(backupDir, destination);
    throw error;
  }
  } finally {
    // Retain the recovery directory if restoring the previous package also fails.
    if (!fs.existsSync(backupDir) || fs.existsSync(destination)) fs.rmSync(transaction, { recursive: true, force: true });
  }

  console.log(`\n✅ Successfully generated Harbor dataset with ${manifest.length} tasks!`);
}

if (import.meta.main) {
  const repository = path.resolve(import.meta.dir, '..');
  const localPython = path.join(repository, '.venv/bin/python');
  const checked = spawnSync(fs.existsSync(localPython) ? localPython : 'python3', [
    '-c', 'from baseline.validate_dataset import require_valid_dataset; require_valid_dataset("dataset/fontbench-2-rendered/manifest.json")',
  ], { cwd: repository, stdio: 'inherit' });
  if (checked.status !== 0) throw new Error('Dataset readiness checks failed; Harbor package was not changed.');
  buildHarborDataset(path.join(repository, 'dataset/fontbench-2-rendered'), path.join(repository, 'dataset/fontbench-2'));
}

