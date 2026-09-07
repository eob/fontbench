#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Open Sans",
  "category": "non-serif",
  "weight": "thin",
  "modifier": "regular",
  "kerning": "normal",
  "line_height": "normal"
}
EOF
