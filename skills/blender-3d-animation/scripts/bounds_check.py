# 逐帧把物体投影到画面，列出越界帧：出画、出 9:16 中间区、跑出指定的父物体（如标题跑出屏幕）
# 在 Blender 里跑（读已保存的 .blend）：
#   Blender -b 镜头.blend -P bounds_check.py -- \
#     --check DuetDisc,DuetCord --check Title@370 --inside Title:Screen \
#     --safe 420,1500 --out check/bounds.json
# --check NAME[,NAME][@起-止]  这些物体合起来算一个包围框；@370 表示从 370 帧查到最后
# --inside A:B                A 的投影必须完全落在 B 的投影内（只在 A 被 --check 的帧里查）
# --safe X0,X1                9:16 中间区的像素范围（按 100% 分辨率；1920 宽默认 420–1500）
# --margin PX                 离画面边缘至少留多少像素（默认 0）
import bpy, sys, json, argparse
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ap = argparse.ArgumentParser()
ap.add_argument("--check", action="append", default=[])
ap.add_argument("--inside", action="append", default=[])
ap.add_argument("--safe", default="420,1500")
ap.add_argument("--margin", type=float, default=0)
ap.add_argument("--frames", default="")
ap.add_argument("--out", default="")
args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

sc = bpy.context.scene
cam = sc.camera
W, H = sc.render.resolution_x, sc.render.resolution_y
safe = [float(v) for v in args.safe.split(",")]
f0, f1 = sc.frame_start, sc.frame_end
if args.frames:
    f0, f1 = map(int, args.frames.split("-"))


def parse_check(s):
    names, _, rng = s.partition("@")
    a, b = f0, f1
    if rng:
        p = rng.split("-")
        a = int(p[0])
        b = int(p[1]) if len(p) > 1 and p[1] else f1
    return [n for n in names.split(",") if n], a, b


checks = [parse_check(s) for s in args.check]
insides = [s.split(":") for s in args.inside]


def world_points(name, dg, limit=1500):
    ob = bpy.data.objects[name]
    ev = ob.evaluated_get(dg)
    try:
        me = ev.to_mesh()
    except RuntimeError:
        me = None
    if me is None or not len(me.vertices):
        pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    else:
        step = max(1, len(me.vertices) // limit)
        pts = [ev.matrix_world @ me.vertices[i].co for i in range(0, len(me.vertices), step)]
        ev.to_mesh_clear()
    return pts


def project(names, dg):
    xs, ys, behind = [], [], False
    for n in names:
        for p in world_points(n, dg):
            v = world_to_camera_view(sc, cam, p)
            if v.z <= 0:
                behind = True
                continue
            xs.append(v.x * W)
            ys.append((1 - v.y) * H)
    if not xs:
        return None
    return dict(x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys), behind=behind)


issues = []
m = args.margin
for f in range(f0, f1 + 1):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    boxes = {}
    for names, a, b in checks:
        if not a <= f <= b:
            continue
        bb = project(names, dg)
        key = ",".join(names)
        boxes[key] = bb
        if bb is None:
            issues.append(dict(frame=f, what=key, kind="不可见"))
            continue
        if bb["behind"] or bb["x0"] < m or bb["x1"] > W - m or bb["y0"] < m or bb["y1"] > H - m:
            issues.append(dict(frame=f, what=key, kind="出画",
                               box=[round(bb["x0"]), round(bb["y0"]), round(bb["x1"]), round(bb["y1"])]))
        if bb["x0"] < safe[0] or bb["x1"] > safe[1]:
            issues.append(dict(frame=f, what=key, kind="出 9:16 区", x=[round(bb["x0"]), round(bb["x1"])]))
    for a_name, b_name in insides:
        inner = next((v for k, v in boxes.items() if a_name in k.split(",")), "skip")
        if inner == "skip" or inner is None:
            continue
        outer = project([b_name], dg)
        if outer is None or inner["x0"] < outer["x0"] or inner["x1"] > outer["x1"] \
                or inner["y0"] < outer["y0"] or inner["y1"] > outer["y1"]:
            issues.append(dict(frame=f, what=a_name, kind=f"超出 {b_name}"))


def ranges(frames):
    out, start, prev = [], None, None
    for f in frames:
        if start is None:
            start = prev = f
        elif f == prev + 1:
            prev = f
        else:
            out.append((start, prev))
            start = prev = f
    if start is not None:
        out.append((start, prev))
    return ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in out)


groups = {}
for it in issues:
    groups.setdefault((it["what"], it["kind"]), []).append(it["frame"])
print("BOUNDS", f"{W}x{H}", "safe", safe, "frames", f"{f0}-{f1}")
if not groups:
    print("BOUNDS OK")
for (what, kind), frames in groups.items():
    print(f"BOUNDS {what} {kind}: {ranges(frames)}")
if args.out:
    json.dump(dict(safe=safe, size=[W, H], issues=issues), open(bpy.path.abspath(args.out) if args.out.startswith("//") else args.out, "w"), ensure_ascii=False, indent=1)
