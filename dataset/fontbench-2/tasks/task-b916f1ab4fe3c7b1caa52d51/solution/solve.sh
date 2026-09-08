#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Bitter",
  "category": "serif",
  "weight": "bold",
  "modifier": "regular",
  "kerning": "normal",
  "line_height": "normal"
}
EOF
