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
  "weight": "bold",
  "modifier": "italic",
  "kerning": "normal",
  "line_height": "loose"
}
EOF
