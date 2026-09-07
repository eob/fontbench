#!/bin/bash
set -euo pipefail

python3 - "$(dirname -- "${BASH_SOURCE[0]}")/ground_truth.json" <<'PY_GRADER'
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
    f.write(f"{score}\n")

print(f"[FontBench-1 Verifier] Task: {gt['taskId']} - Score: {score*100:.1f}%")
print(f"  Font: {'PASS' if font_pass else 'FAIL'} | Cat: {'PASS' if cat_pass else 'FAIL'} | Weight: {'PASS' if weight_pass else 'FAIL'}")
PY_GRADER
