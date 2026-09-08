#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Roboto",
  "category": "non-serif",
  "weight": "black",
  "modifier": "strikethrough",
  "kerning": "normal",
  "line_height": "normal"
}
EOF
