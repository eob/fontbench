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
  "kerning": "tight",
  "line_height": "normal"
}
EOF
