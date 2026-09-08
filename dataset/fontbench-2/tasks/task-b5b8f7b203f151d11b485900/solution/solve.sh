#!/bin/bash
set -euo pipefail

target="/workspace/output.json"
if [ ! -d "/workspace" ]; then
  target="output.json"
fi

cat << 'EOF' > "$target"
{
  "font": "Source Sans 3",
  "category": "non-serif",
  "weight": "regular",
  "modifier": "regular",
  "kerning": "loose",
  "line_height": "loose"
}
EOF
