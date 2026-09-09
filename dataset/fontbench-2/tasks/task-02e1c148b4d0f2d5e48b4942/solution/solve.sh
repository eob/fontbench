#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Lato",
  "category": "non-serif",
  "weight": "bold",
  "modifier": "strikethrough",
  "kerning": "loose",
  "line_height": "loose"
}
EOF
