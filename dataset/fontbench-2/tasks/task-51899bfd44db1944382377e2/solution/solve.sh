#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Libre Baskerville",
  "category": "serif",
  "weight": "bold",
  "modifier": "underline",
  "kerning": "normal",
  "line_height": "tight"
}
EOF
