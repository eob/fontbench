#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "EB Garamond",
  "category": "serif",
  "weight": "black",
  "modifier": "regular",
  "kerning": "normal",
  "line_height": "normal"
}
EOF
