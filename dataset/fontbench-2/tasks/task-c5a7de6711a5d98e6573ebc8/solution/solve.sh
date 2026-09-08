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
  "modifier": "regular",
  "kerning": "tight",
  "line_height": "tight"
}
EOF
