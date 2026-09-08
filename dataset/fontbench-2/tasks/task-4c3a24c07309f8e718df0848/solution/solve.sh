#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Cormorant Garamond",
  "category": "serif",
  "weight": "bold",
  "modifier": "underline",
  "kerning": "tight",
  "line_height": "loose"
}
EOF
