#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "JetBrains Mono",
  "category": "mono",
  "weight": "regular",
  "modifier": "small-caps",
  "kerning": "loose",
  "line_height": "tight"
}
EOF
