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
  "weight": "black",
  "modifier": "regular",
  "kerning": "loose",
  "line_height": "loose"
}
EOF
