#!/usr/bin/env bash
# 把一组 PNG 拼成审片总览图。
# 用法：sheet.sh '<glob>' <列数> <输出.png> [每格宽度，默认 640]
#   sheet.sh 'check/stills/s*.png' 3 check/stills_sheet.png
# 从成片抽帧：sheet.sh --video out.mp4 '0,60,90,150,270,400' 3 sheet.png
set -euo pipefail
if [ "$1" = "--video" ]; then
  video=$2; frames=$3; cols=$4; out=$5; w=${6:-640}
  sel=$(echo "$frames" | tr ',' '\n' | sed 's/.*/eq(n\\,&)/' | paste -sd+ -)
  n=$(echo "$frames" | tr ',' '\n' | wc -l | tr -d ' ')
  rows=$(( (n + cols - 1) / cols ))
  ffmpeg -v error -y -i "$video" -vf "select='$sel',scale=$w:-1,tile=${cols}x${rows}" -frames:v 1 "$out"
else
  pattern=$1; cols=$2; out=$3; w=${4:-640}
  n=$(ls $pattern | wc -l | tr -d ' ')
  rows=$(( (n + cols - 1) / cols ))
  ffmpeg -v error -y -pattern_type glob -i "$pattern" -vf "scale=$w:-1,tile=${cols}x${rows}" -frames:v 1 "$out"
fi
echo "wrote $out"
