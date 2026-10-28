# 裁掉浏览器顶栏，给私人信息打马赛克，生成屏幕贴图。用法: python3 prep_textures.py
import subprocess, pathlib
P = pathlib.Path(__file__).resolve().parents[2]
SRC, OUT = P / "素材", P / "输出/开头动效/textures"

def mosaic(src, dst, top, rects, block=22):
    # rects: 原图坐标 (x, y, w, h)；最后裁掉 top 像素（浏览器标签栏+地址栏）
    chains, last = [], "0:v"
    for i, (x, y, w, h) in enumerate(rects):
        chains.append(f"[0:v]crop={w}:{h}:{x}:{y},scale={max(1,w//block)}:{max(1,h//block)},scale={w}:{h}:flags=neighbor[m{i}]")
        chains.append(f"[{last}][m{i}]overlay={x}:{y}[o{i}]")
        last = f"o{i}"
    chains.append(f"[{last}]crop=iw:ih-{top}:0:{top}[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", ";".join(chains),
                    "-map", "[out]", str(dst)], check=True)

# 主界面 3440x2058：三段私人消息 + 底部淡出那行 + 左下头像
mosaic(SRC / "laptop_main.png", OUT / "laptop_main.png", 168, [
    (1264, 774, 990, 164), (1264, 1010, 840, 132), (1264, 1400, 990, 124),
    (1300, 1850, 700, 42), (14, 1976, 58, 58)])
# 剧本文档 2000x1194：真名署名、左下头像
mosaic(SRC / "laptop_script_doc.png", OUT / "laptop_script_doc.png", 95, [
    (1124, 326, 100, 26), (8, 1142, 34, 34)], block=8)
