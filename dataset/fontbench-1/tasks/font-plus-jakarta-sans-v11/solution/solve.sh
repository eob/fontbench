#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Plus Jakarta Sans",
  "category": "non-serif",
  "weight": "bold",
  "modifier": "regular",
  "kerning": "tight",
  "line_height": "loose"
}
EOF
