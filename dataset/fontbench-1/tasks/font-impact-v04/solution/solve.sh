#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Impact",
  "category": "other",
  "weight": "black",
  "modifier": "strikethrough",
  "kerning": "normal",
  "line_height": "normal"
}
EOF
