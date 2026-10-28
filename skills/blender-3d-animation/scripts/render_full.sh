#!/usr/bin/env bash
# 后台渲全片 + 防睡眠 + 合成 H.264。用 Bash 的 run_in_background 跑它。
# 用法：render_full.sh <场景脚本.py> <输出目录> <成片名.mp4> [fps，默认 30]
# 场景脚本需支持 `-- full` 模式，把帧写到 <输出目录>/frames/f_####.png
set -euo pipefail
script=$1; out=$2; mp4=$3; fps=${4:-30}
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
cd "$out"
date
"$BLENDER" -b --factory-startup -P "$script" -- full > full_render_log.txt 2>&1 &
pid=$!
caffeinate -i -s -w $pid &   # 渲完自动解除；合盖仍会睡眠
wait $pid
date
if grep -q Traceback full_render_log.txt; then grep -A8 Traceback full_render_log.txt; exit 1; fi
ls frames | wc -l
ffmpeg -v error -y -framerate "$fps" -start_number 0 -i frames/f_%04d.png \
  -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow -movflags +faststart "$mp4"
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate,nb_frames -of compact "$mp4"
