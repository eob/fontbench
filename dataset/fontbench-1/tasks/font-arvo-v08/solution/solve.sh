#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Arvo",
  "category": "serif",
  "weight": "black",
  "modifier": "underline",
  "kerning": "tight",
  "line_height": "loose"
}
EOF
