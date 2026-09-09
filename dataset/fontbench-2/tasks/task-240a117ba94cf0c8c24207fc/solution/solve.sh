#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Spectral",
  "category": "serif",
  "weight": "bold",
  "modifier": "strikethrough",
  "kerning": "normal",
  "line_height": "normal"
}
EOF
