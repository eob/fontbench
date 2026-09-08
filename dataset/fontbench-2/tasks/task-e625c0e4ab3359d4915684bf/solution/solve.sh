#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Raleway",
  "category": "non-serif",
  "weight": "bold",
  "modifier": "strikethrough",
  "kerning": "normal",
  "line_height": "normal"
}
EOF
