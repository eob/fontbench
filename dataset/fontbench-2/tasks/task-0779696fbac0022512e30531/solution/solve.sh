#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Playfair Display",
  "category": "serif",
  "weight": "black",
  "modifier": "regular",
  "kerning": "loose",
  "line_height": "loose"
}
EOF
