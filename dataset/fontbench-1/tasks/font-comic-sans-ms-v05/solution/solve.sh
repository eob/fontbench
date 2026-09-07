#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Comic Sans MS",
  "category": "handwriting",
  "weight": "thin",
  "modifier": "small-caps",
  "kerning": "tight",
  "line_height": "loose"
}
EOF
