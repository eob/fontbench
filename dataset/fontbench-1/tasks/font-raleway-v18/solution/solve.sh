#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Raleway",
  "category": "non-serif",
  "weight": "regular",
  "modifier": "underline",
  "kerning": "loose",
  "line_height": "tight"
}
EOF
