#!/usr/bin/env python3
"""把截图做成屏幕贴图：先在原图坐标上打马赛克，再裁掉状态栏/浏览器栏。只用 ffmpeg。

例：
  python3 prep_screens.py 素材/laptop_main.png textures/laptop_main.png \
      --top 168 --mosaic 1264,774,990,164 --mosaic 14,1976,58,58
坐标都是原图像素 (x,y,w,h)；--top/--bottom/--left/--right 是最后裁掉的像素数。
"""
import argparse
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--bottom", type=int, default=0)
    ap.add_argument("--left", type=int, default=0)
    ap.add_argument("--right", type=int, default=0)
    ap.add_argument("--mosaic", action="append", default=[], help="x,y,w,h（原图坐标），可重复")
    ap.add_argument("--block", type=int, default=22, help="马赛克块大小（像素）")
    a = ap.parse_args()

    chains, last = [], "0:v"
    for i, r in enumerate(a.mosaic):
        x, y, w, h = map(int, r.split(","))
        b = a.block
        chains.append(f"[0:v]crop={w}:{h}:{x}:{y},scale={max(1, w // b)}:{max(1, h // b)},scale={w}:{h}:flags=neighbor[m{i}]")
        chains.append(f"[{last}][m{i}]overlay={x}:{y}:format=rgb[o{i}]")
        last = f"o{i}"
    crop = f"crop=iw-{a.left + a.right}:ih-{a.top + a.bottom}:{a.left}:{a.top}"
    chains.append(f"[{last}]{crop}[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src, "-filter_complex", ";".join(chains),
                    "-map", "[out]", a.dst], check=True)
    print("wrote", a.dst)


if __name__ == "__main__":
    main()
