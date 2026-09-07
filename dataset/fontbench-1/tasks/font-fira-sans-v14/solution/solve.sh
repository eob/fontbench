#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Fira Sans",
  "category": "non-serif",
  "weight": "regular",
  "modifier": "strikethrough",
  "kerning": "tight",
  "line_height": "loose"
}
EOF
