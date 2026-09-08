#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Roboto Mono",
  "category": "mono",
  "weight": "bold",
  "modifier": "small-caps",
  "kerning": "tight",
  "line_height": "normal"
}
EOF
