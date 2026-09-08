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
    f.write(f"{score}\n")

print(f"[FontBench-2 Verifier] Task: {gt['taskId']} - Score: {score*100:.1f}%")
print(f"  Font: {'PASS' if font_pass else 'FAIL'} | Cat: {'PASS' if cat_pass else 'FAIL'} | Weight: {'PASS' if weight_pass else 'FAIL'}")
PY_GRADER
