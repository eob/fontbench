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
  const tasksDir = path.join(outputDir, 'tasks');
  fs.mkdirSync(tasksDir, { recursive: true });

  console.log(`Generating Harbor dataset at ${outputDir} for ${manifest.length} tasks...`);

  // 1. Generate top-level dataset.toml
  const datasetToml = `version = "1.0"

[dataset]
name = "fontbench-1"
version = "1.1.0"
description = "FontBench-1: Multi-attribute visual typography benchmark across 50 top fonts and 5 typographic dimensions (font, category, weight, modifiers, spacing)."
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
    if (fs.existsSync(srcImg)) {
      fs.copyFileSync(srcImg, destImg);
    }

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
  "font": "${sample.fontName}",
  "category": "${sample.category}",
  "weight": "${sample.weight}",
  "modifier": "${sample.modifier}",
  "kerning": "${sample.kerning}",
  "line_height": "${sample.lineHeight}"
}
\`\`\`
`;
    fs.writeFileSync(path.join(taskDir, 'instruction.md'), instructionMd, 'utf-8');

    // environment/Dockerfile
    const dockerfile = `FROM alpine:3.19
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
{
  "font": "${sample.fontName}",
  "category": "${sample.category}",
  "weight": "${sample.weight}",
  "modifier": "${sample.modifier}",
  "kerning": "${sample.kerning}",
  "line_height": "${sample.lineHeight}"
}
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

python3 - <<'PY_GRADER'
import json, os, re, sys

with open("ground_truth.json", "r", encoding="utf-8") as f:
    gt = json.load(f)

def normalize(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', text.lower())

candidate_paths = [
    "/workspace/output.json",
    "./output.json",
    "output.json",
    "../output.json",
    "../../output.json"
]

data = {}
for p in candidate_paths:
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                break
        except Exception:
            pass

pred_font = normalize(str(data.get("font", "")))
accepted_names = [gt["canonical"]] + gt.get("aliases", [])
accepted_norms = [normalize(a) for a in accepted_names if a]
font_pass = any(a in pred_font or pred_font in a for a in accepted_norms) if pred_font else False

cat_pass = normalize(str(data.get("category", ""))) in normalize(gt["category"])
weight_pass = normalize(str(data.get("weight", ""))) in normalize(gt["weight"])
mod_pass = normalize(str(data.get("modifier", ""))) in normalize(gt["modifier"])
kern_pass = normalize(str(data.get("kerning", ""))) in normalize(gt["kerning"])
lh_pass = normalize(str(data.get("line_height", ""))) in normalize(gt["lineHeight"])

score = sum([font_pass, cat_pass, weight_pass, mod_pass, kern_pass, lh_pass]) / 6.0
passed = font_pass and cat_pass

logs_dir = os.environ.get("HARBOR_LOGS_DIR", "")
if not logs_dir:
    logs_dir = "/logs/verifier" if os.path.exists("/logs") and os.access("/logs", os.W_OK) else "./logs/verifier"

os.makedirs(logs_dir, exist_ok=True)
reward_path = os.path.join(logs_dir, "reward.txt")
with open(reward_path, "w", encoding="utf-8") as f:
    f.write(f"{score:.2f}\\n")

print(f"[FontBench-1 Verifier] Task: {gt['taskId']} - Score: {score*100:.1f}%")
print(f"  Font: {'PASS' if font_pass else 'FAIL'} | Cat: {'PASS' if cat_pass else 'FAIL'} | Weight: {'PASS' if weight_pass else 'FAIL'}")
if not passed:
    sys.exit(1)
PY_GRADER
`;
    const testPath = path.join(testsDir, 'test.sh');
    fs.writeFileSync(testPath, testSh, 'utf-8');
    fs.chmodSync(testPath, 0o755);
  }

  console.log(`\n✅ Successfully generated Harbor dataset with ${manifest.length} tasks!`);
}

if (import.meta.main) {
  buildHarborDataset();
}
