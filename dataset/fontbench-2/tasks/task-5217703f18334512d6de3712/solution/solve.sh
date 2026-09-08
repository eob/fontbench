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
  "weight": "bold",
  "modifier": "italic",
  "kerning": "loose",
  "line_height": "tight"
}
EOF
