#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Pacifico",
  "category": "handwriting",
  "weight": "regular",
  "modifier": "small-caps",
  "kerning": "normal",
  "line_height": "loose"
}
EOF
