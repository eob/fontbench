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
  "weight": "thin",
  "modifier": "italic",
  "kerning": "tight",
  "line_height": "normal"
}
EOF
