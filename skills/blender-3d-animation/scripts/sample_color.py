#!/usr/bin/env python3
"""在渲染帧上取 6x6 像素均值，和目标色比较。

两种用法：
  python3 sample_color.py --points check/sample_points.json --dir check/stills --target D0744E
      points.json 由场景脚本写出：[{frame, visible, x, y}, ...]，文件名里要有 _f0123
  python3 sample_color.py --at check/stills/s03_f0079.png 329 453 --target D0744E
      手动指定一个点（自动点落在绳子、高光或阴影上时用）
"""
import argparse
import glob
import json
import subprocess


def sample(png, x, y, n=6):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", png, "-vf",
                          f"crop={n}:{n}:{x - n // 2}:{y - n // 2},scale=1:1:flags=area",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return tuple(raw[:3])


def report(label, rgb, target):
    t = tuple(int(target[i:i + 2], 16) for i in (0, 2, 4))
    d = tuple(c - tc for c, tc in zip(rgb, t))
    print(f"{label}: #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X} {rgb}  目标 #{target} {t}  差 {d}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--points")
    ap.add_argument("--dir")
    ap.add_argument("--at", nargs=3, metavar=("PNG", "X", "Y"))
    ap.add_argument("--target", default="D0744E")
    a = ap.parse_args()
    if a.at:
        report(a.at[0], sample(a.at[0], int(a.at[1]), int(a.at[2])), a.target.upper())
        return
    for p in json.load(open(a.points)):
        if not p.get("visible"):
            continue
        hits = glob.glob(f"{a.dir}/*_f{p['frame']:04d}.png")
        if hits:
            report(f"f{p['frame']}", sample(hits[0], p["x"], p["y"]), a.target.upper())


if __name__ == "__main__":
    main()
