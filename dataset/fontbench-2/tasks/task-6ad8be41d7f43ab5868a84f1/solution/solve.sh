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
  "weight": "regular",
  "modifier": "small-caps",
  "kerning": "tight",
  "line_height": "normal"
}
EOF
