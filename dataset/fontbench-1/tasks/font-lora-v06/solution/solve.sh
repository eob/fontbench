#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Lora",
  "category": "serif",
  "weight": "regular",
  "modifier": "regular",
  "kerning": "loose",
  "line_height": "tight"
}
EOF
