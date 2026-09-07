import fs from 'node:fs';
import path from 'node:path';
import type { RenderedSampleMeta } from './render';

export function buildHarborDataset(
  renderedDir: string = 'dataset/rendered',
  outputDir: string = 'dataset/fontbench-1'
) {
  const manifestPath = path.join(renderedDir, 'manifest.json');
  if (!fs.existsSync(manifestPath)) {
    throw new Error(`Manifest not found at ${manifestPath}. Run rendering first.`);
  }

  const manifest: RenderedSampleMeta[] = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
  if (!Array.isArray(manifest)) throw new Error('Manifest must contain an array of samples.');
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
  }
  const tasksDir = path.join(outputDir, 'tasks');
  const staleTasks: string[] = [];
  if (fs.existsSync(tasksDir)) {
    if (fs.lstatSync(tasksDir).isSymbolicLink()) throw new Error(`Task directory cannot be a symlink: ${tasksDir}`);
    for (const entry of fs.readdirSync(tasksDir, { withFileTypes: true })) {
      const taskDir = path.join(tasksDir, entry.name);
      if (!entry.isDirectory()) throw new Error(`Unexpected task entry: ${taskDir}`);
      if (taskIds.has(entry.name)) continue;
      const expectedFiles = [
        'task.toml', 'instruction.md', 'environment', 'environment/Dockerfile', 'environment/sample.png',
        'solution', 'solution/solve.sh', 'tests', 'tests/test.sh', 'tests/ground_truth.json',
      ];
      const entries = fs.readdirSync(taskDir, { recursive: true, encoding: 'utf8' });
      if (entries.length !== expectedFiles.length || entries.some(file => !expectedFiles.includes(file)
        || fs.lstatSync(path.join(taskDir, file)).isSymbolicLink())
        || JSON.parse(fs.readFileSync(path.join(taskDir, 'tests', 'ground_truth.json'), 'utf8')).taskId !== entry.name) {
        throw new Error(`Refusing to remove unrecognized stale task directory: ${taskDir}`);
      }
      staleTasks.push(taskDir);
    }
  }
  fs.mkdirSync(tasksDir, { recursive: true });

  console.log(`Generating Harbor dataset at ${outputDir} for ${manifest.length} tasks...`);

  // 1. Generate top-level dataset.toml
  const datasetToml = `version = "1.0"

[dataset]
name = "fontbench-1"
version = "1.1.0"
description = "FontBench-1: Visual typography benchmark across six attributes: font, category, weight, modifier, kerning, and line height."
author = "Edward Benson"
license = "MIT"
task_dir = "tasks"

[metadata]
total_tasks = ${manifest.length}
primary_pangram = "The quick brown fox jumps over the lazy dog."
`;
  fs.writeFileSync(path.join(outputDir, 'dataset.toml'), datasetToml, 'utf-8');

  // 2. Generate each task directory
  for (const sample of manifest) {
    const taskDir = path.join(tasksDir, sample.taskId);
    const envDir = path.join(taskDir, 'environment');
    const solDir = path.join(taskDir, 'solution');
    const testsDir = path.join(taskDir, 'tests');

    fs.mkdirSync(envDir, { recursive: true });
    fs.mkdirSync(solDir, { recursive: true });
    fs.mkdirSync(testsDir, { recursive: true });

    // Copy sample image to environment/sample.png
    const srcImg = path.join(renderedDir, sample.imageFilename);
    const destImg = path.join(envDir, 'sample.png');
    fs.copyFileSync(srcImg, destImg);

    // task.toml
    const taskToml = `version = "1.0"

[metadata]
name = "${sample.taskId}"
author_name = "Edward Benson"
difficulty = "medium"
category = "vision"
tags = ["typography", "font-identification", "vlm", "${sample.category}", "${sample.weight}", "${sample.modifier}", "${sample.widthId}"]

[agent]
timeout_sec = 180.0

[verifier]
timeout_sec = 60.0
`;
    fs.writeFileSync(path.join(taskDir, 'task.toml'), taskToml, 'utf-8');

    // instruction.md
    const instructionMd = `# FontBench-1 Task: Identify Rendered Typographic Properties

Examine the rendered text sample located at \`./sample.png\`.

The image displays the English pangram:
> *"${sample.pangram}"*

### Your Objective
Identify the 6 typographic properties used to typeset this text:
1. **font**: The canonical font family name (e.g., Arial, Times New Roman, Roboto, Georgia, etc.)
2. **category**: Exactly one of [serif, non-serif, mono, handwriting, other]
3. **weight**: Exactly one of [thin, regular, bold, black]
4. **modifier**: Exactly one of [regular, italic, underline, strikethrough, small-caps]
5. **kerning**: Exactly one of [tight, normal, loose]
6. **line_height**: Exactly one of [tight, normal, loose]

### Required Output
Write **only** a valid JSON object into \`/workspace/output.json\` (or \`./output.json\`):

\`\`\`json
{
  "font": "<font name>",
  "category": "<serif|non-serif|mono|handwriting|other>",
  "weight": "<thin|regular|bold|black>",
  "modifier": "<regular|italic|underline|strikethrough|small-caps>",
  "kerning": "<tight|normal|loose>",
  "line_height": "<tight|normal|loose>"
}
\`\`\`
`;
    fs.writeFileSync(path.join(taskDir, 'instruction.md'), instructionMd, 'utf-8');

    // environment/Dockerfile
    const dockerfile = `FROM alpine:3.24
RUN apk add --no-cache bash python3
WORKDIR /workspace
COPY sample.png /workspace/sample.png
`;
    fs.writeFileSync(path.join(envDir, 'Dockerfile'), dockerfile, 'utf-8');

    // solution/solve.sh
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

    // tests/ground_truth.json
    const groundTruth = {
      taskId: sample.taskId,
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

    // tests/test.sh
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

data = {}
for p in candidate_paths:
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                value = json.load(f)
                data = value if isinstance(value, dict) else {}
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

print(f"[FontBench-1 Verifier] Task: {gt['taskId']} - Score: {score*100:.1f}%")
print(f"  Font: {'PASS' if font_pass else 'FAIL'} | Cat: {'PASS' if cat_pass else 'FAIL'} | Weight: {'PASS' if weight_pass else 'FAIL'}")
PY_GRADER
`;
    const testPath = path.join(testsDir, 'test.sh');
    fs.writeFileSync(testPath, testSh, 'utf-8');
    fs.chmodSync(testPath, 0o755);
  }

  for (const taskDir of staleTasks) fs.rmSync(taskDir, { recursive: true });

  console.log(`\n✅ Successfully generated Harbor dataset with ${manifest.length} tasks!`);
}

if (import.meta.main) {
  buildHarborDataset();
}
