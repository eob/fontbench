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
  "weight": "thin",
  "modifier": "strikethrough",
  "kerning": "loose",
  "line_height": "tight"
}
EOF
