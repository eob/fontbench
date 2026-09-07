#!/bin/bash
set -euo pipefail

target="/workspace/output.txt"
if [ ! -d "/workspace" ]; then
  target="output.txt"
fi

echo "Inter" > "$target"
