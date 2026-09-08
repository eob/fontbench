#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Noto Sans",
  "category": "non-serif",
  "weight": "bold",
  "modifier": "underline",
  "kerning": "loose",
  "line_height": "normal"
}
EOF
