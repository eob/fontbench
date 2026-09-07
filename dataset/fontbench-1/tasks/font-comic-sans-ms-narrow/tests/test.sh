#!/bin/bash
set -euo pipefail

python3 - <<'PY_GRADER'
import json, os, re, sys

with open("ground_truth.json", "r", encoding="utf-8") as f:
    gt = json.load(f)

def normalize(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', text.lower())

candidate_paths = [
    "/workspace/output.txt",
    "./output.txt",
    "output.txt",
    "../output.txt",
    "../../output.txt"
]

pred_raw = ""
for p in candidate_paths:
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                pred_raw = f.read().strip()
                break
        except Exception:
            pass

pred_norm = normalize(pred_raw)
accepted_names = [gt["canonical"]] + gt.get("aliases", [])
accepted_norms = [normalize(a) for a in accepted_names if a]

# Check if any accepted canonical/alias is contained in normalized prediction
passed = any(acc in pred_norm for acc in accepted_norms) if pred_norm else False
reward = 1.0 if passed else 0.0

logs_dir = os.environ.get("HARBOR_LOGS_DIR", "")
if not logs_dir:
    logs_dir = "/logs/verifier" if os.path.exists("/logs") and os.access("/logs", os.W_OK) else "./logs/verifier"

os.makedirs(logs_dir, exist_ok=True)
reward_path = os.path.join(logs_dir, "reward.txt")
with open(reward_path, "w", encoding="utf-8") as f:
    f.write(f"{reward:.1f}\n")

print(f"[FontBench-1 Verifier] Task: {gt['taskId']}")
print(f"  Target:     {gt['canonical']} (aliases: {gt.get('aliases', [])})")
print(f"  Prediction: '{pred_raw}' (normalized: '{pred_norm}')")
print(f"  Result:     {'PASS' if passed else 'FAIL'} (reward={reward})")

if not passed:
    sys.exit(1)
PY_GRADER
