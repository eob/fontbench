#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Caveat",
  "category": "handwriting",
  "weight": "regular",
  "modifier": "italic",
  "kerning": "tight",
  "line_height": "loose"
}
EOF
