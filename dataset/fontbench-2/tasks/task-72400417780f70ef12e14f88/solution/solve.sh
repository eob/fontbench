#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Source Sans 3",
  "category": "non-serif",
  "weight": "black",
  "modifier": "small-caps",
  "kerning": "tight",
  "line_height": "normal"
}
EOF
