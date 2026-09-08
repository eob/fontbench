#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Merriweather",
  "category": "serif",
  "weight": "black",
  "modifier": "strikethrough",
  "kerning": "loose",
  "line_height": "loose"
}
EOF
