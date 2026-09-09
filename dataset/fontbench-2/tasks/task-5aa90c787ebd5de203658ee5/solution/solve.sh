#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Cinzel",
  "category": "serif",
  "weight": "black",
  "modifier": "underline",
  "kerning": "loose",
  "line_height": "normal"
}
EOF
