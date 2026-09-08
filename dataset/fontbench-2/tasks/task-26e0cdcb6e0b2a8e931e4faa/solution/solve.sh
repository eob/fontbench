#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Helvetica",
  "category": "non-serif",
  "weight": "regular",
  "modifier": "underline",
  "kerning": "tight",
  "line_height": "loose"
}
EOF
