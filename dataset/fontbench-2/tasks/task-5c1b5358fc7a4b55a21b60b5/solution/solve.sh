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
  "weight": "thin",
  "modifier": "regular",
  "kerning": "loose",
  "line_height": "loose"
}
EOF
