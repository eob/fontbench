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
  "weight": "regular",
  "modifier": "italic",
  "kerning": "normal",
  "line_height": "loose"
}
EOF
