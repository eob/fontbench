#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Georgia",
  "category": "serif",
  "weight": "thin",
  "modifier": "underline",
  "kerning": "normal",
  "line_height": "normal"
}
EOF
