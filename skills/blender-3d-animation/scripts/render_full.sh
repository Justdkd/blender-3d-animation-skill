#!/usr/bin/env bash
# 后台渲全片 + 防睡眠 + 合成 H.264。用 Bash 的 run_in_background 跑它。
# 用法：render_full.sh <场景脚本.py> <输出目录> <成片名.mp4> [fps，默认 30]
# 场景脚本需支持 `-- full` 模式，把帧写到 <输出目录>/frames/f_####.png，
# 并设 render.use_overwrite=False、use_placeholder=True：中途睡眠或崩溃后，原样再跑一次就从断点续渲。
set -euo pipefail
script=$1; out=$2; mp4=$3; fps=${4:-30}
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
cd "$out"
mkdir -p frames
# 上次中断时留下的占位帧（0 字节）或写了一半的帧要删掉，否则会被当成已渲好跳过
find frames -name 'f_*.png' -size -2k -print -delete
done_n=$(find frames -name 'f_*.png' | wc -l | tr -d ' ')
[ "$done_n" -gt 0 ] && echo "续渲：已有 $done_n 帧，跳过"
date
"$BLENDER" -b --factory-startup -P "$script" -- full >> full_render_log.txt 2>&1 &
pid=$!
caffeinate -i -s -w $pid &   # 渲完自动解除；合盖仍会睡眠
wait $pid
date
if grep -q Traceback full_render_log.txt; then grep -A8 Traceback full_render_log.txt; exit 1; fi
bad=$(find frames -name 'f_*.png' -size -2k | wc -l | tr -d ' ')
if [ "$bad" -gt 0 ]; then echo "有 $bad 帧是占位或损坏，重跑本脚本续渲"; exit 1; fi
ls frames | wc -l
ffmpeg -v error -y -framerate "$fps" -start_number 0 -i frames/f_%04d.png \
  -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow -movflags +faststart "$mp4"
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate,nb_frames -of compact "$mp4"
