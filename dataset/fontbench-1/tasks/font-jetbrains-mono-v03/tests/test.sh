#!/bin/bash
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
    f.write(f"{score:.2f}\n")

print(f"[FontBench-1 Verifier] Task: {gt['taskId']} - Score: {score*100:.1f}%")
print(f"  Font: {'PASS' if font_pass else 'FAIL'} | Cat: {'PASS' if cat_pass else 'FAIL'} | Weight: {'PASS' if weight_pass else 'FAIL'}")
if not passed:
    sys.exit(1)
PY_GRADER
