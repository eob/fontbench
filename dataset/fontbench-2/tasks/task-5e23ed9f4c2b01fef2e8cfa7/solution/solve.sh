#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Crimson Text",
  "category": "serif",
  "weight": "regular",
  "modifier": "underline",
  "kerning": "loose",
  "line_height": "normal"
}
EOF
