#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Inter",
  "category": "non-serif",
  "weight": "black",
  "modifier": "italic",
  "kerning": "normal",
  "line_height": "loose"
}
EOF
