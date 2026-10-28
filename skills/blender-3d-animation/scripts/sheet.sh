#!/usr/bin/env bash
# 把一组 PNG 拼成审片总览图。
# 用法：sheet.sh '<glob>' <列数> <输出.png> [每格宽度，默认 640]
#   sheet.sh 'check/stills/s*.png' 3 check/stills_sheet.png
# 从成片抽帧：sheet.sh --video out.mp4 '0,60,90,150,270,400' 3 sheet.png
# 手机小图：sheet.sh --phone '<glob>' <输出.png>
#   每格缩到 360px 宽，3 列
# 连帧条：sheet.sh --strip <场景脚本> <起始帧> <输出.png>
#   用该脚本的 -- probe 渲出起始帧起连续 12 帧，再拼 6×2
#   帧文件读 <脚本目录>/check/probe/p_f####.png（与 duet_opening.py 的 probe 一致）
set -euo pipefail
if [ "$1" = "--video" ]; then
  video=$2; frames=$3; cols=$4; out=$5; w=${6:-640}
  sel=$(echo "$frames" | tr ',' '\n' | sed 's/.*/eq(n\\,&)/' | paste -sd+ -)
  n=$(echo "$frames" | tr ',' '\n' | wc -l | tr -d ' ')
  rows=$(( (n + cols - 1) / cols ))
  ffmpeg -v error -y -i "$video" -vf "select='$sel',scale=$w:-1,tile=${cols}x${rows}" -frames:v 1 "$out"
elif [ "$1" = "--phone" ]; then
  pattern=$2; out=$3; cols=3; w=360
  n=$(ls $pattern | wc -l | tr -d ' ')
  rows=$(( (n + cols - 1) / cols ))
  ffmpeg -v error -y -pattern_type glob -i "$pattern" -vf "scale=$w:-1,tile=${cols}x${rows}" -frames:v 1 "$out"
elif [ "$1" = "--strip" ]; then
  script=$2; start=$3; out=$4
  BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
  frames=$(seq "$start" $((start + 11)) | paste -sd, -)
  "$BLENDER" -b --factory-startup -P "$script" -- probe "$frames"
  scriptdir=$(cd "$(dirname "$script")" && pwd)
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  for i in $(seq 0 11); do
    printf -v name "p_f%04d.png" $((start + i))
    ln -s "$scriptdir/check/probe/$name" "$tmp/$(printf '%02d.png' "$i")"
  done
  ffmpeg -v error -y -pattern_type glob -i "$tmp/*.png" -vf "tile=6x2" -frames:v 1 "$out"
else
  pattern=$1; cols=$2; out=$3; w=${4:-640}
  n=$(ls $pattern | wc -l | tr -d ' ')
  rows=$(( (n + cols - 1) / cols ))
  ffmpeg -v error -y -pattern_type glob -i "$pattern" -vf "scale=$w:-1,tile=${cols}x${rows}" -frames:v 1 "$out"
fi
echo "wrote $out"
