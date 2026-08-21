#!/usr/bin/env bash
# Desk-cam burst: 5 frames at 2 fps (0.5 s apart) from
# "MacBook Air桌上视角相机". Index shifts when Continuity cameras appear —
# match by name, never hardcode [1].
set -euo pipefail

tag=${1:?tag e.g. pclk64}
out=${2:-/tmp/kebab-cam}
mkdir -p "$out"

list=$(ffmpeg -f avfoundation -list_devices true -i "" 2>&1 || true)
idx=$(printf '%s\n' "$list" | python3 -c '
import re, sys
for line in sys.stdin:
    if "MacBook Air桌上视角相机" in line and "pineapple" not in line.lower():
        # ffmpeg prefixes "[AVFoundation indev @ 0x…] [N] name"
        nums = re.findall(r"\[(\d+)\]", line)
        if nums:
            print(nums[-1])
            break
else:
    sys.exit("desk camera not listed")
')
[ -n "$idx" ]

rm -f "$out/desk-${tag}-"*.jpg
ffmpeg -y -hide_banner -loglevel warning \
  -f avfoundation -framerate 30 -video_size 1920x1440 -pixel_format uyvy422 \
  -i "$idx" -vf fps=2 -frames:v 6 \
  "$out/desk-${tag}-%02d.jpg"
ls -l "$out/desk-${tag}-"*.jpg
