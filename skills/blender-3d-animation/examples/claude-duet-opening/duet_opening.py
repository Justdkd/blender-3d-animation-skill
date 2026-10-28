# Claude Duet 实机演示 · 15 秒 3D 开头（Blender 5，Cycles/Metal）
# 用法：Blender -b -P duet_opening.py -- <mode>
#   build     只建场景并保存 .blend
#   textures  三张屏幕贴图在物体上的正面检查图
#   check     接触表（0/60/90/150/270/400）+ 18 张半分辨率静帧 + 取色点
#   full      全部 450 帧 PNG（MP4 用 ffmpeg 另合）
import bpy, math, random, sys, os, json, glob
from mathutils import Vector, Quaternion, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "textures")
CHECK = os.path.join(HERE, "check")
TEX_MAIN = os.path.join(TEX, "laptop_main.png")
TEX_DOC = os.path.join(TEX, "laptop_script_doc.png")
# 手机截图与 7 行（周一到周日）的像素上下边界；换真截图时写 phone_rows.json 覆盖
PHONE = {"path": os.path.join(TEX, "phone_PLACEHOLDER.png"), "h": 2868,
         "rows": [[600 + i * 240, 800 + i * 240] for i in range(7)]}
if os.path.exists(os.path.join(HERE, "phone_rows.json")):
    PHONE.update(json.load(open(os.path.join(HERE, "phone_rows.json"))))
    PHONE["path"] = os.path.join(TEX, PHONE["path"])

FPS, FRAMES = 30, 450
R, T = 0.035, 0.014           # 毛毡圆片半径 / 厚度（米）
TUBE = 0.07 * R               # 毛毡绳半径
KEY_E = float(os.environ.get("KEY_E", 22))
BASE_SCALE = float(os.environ.get("BASE_SCALE", 1.0))
ICON_K = 0.6                  # 屏幕上 2D 图标相对圆片的大小
DISC_HEX, CORD_ICON_HEX = "D0744E", "8E3F25"
SCREEN_W, SCREEN_ASPECT = 0.296, 3440 / 1890
SCREEN_H = SCREEN_W / SCREEN_ASPECT
SCREEN_Z = 0.108              # 屏幕中心在屏盖局部坐标的高度
LID_TILT = math.radians(-15)
PHONE_C, PHONE_L = Vector((0.30, -0.035, 0.0)), 0.142
PHONE_W = PHONE_L / 2.1727    # 1320x2868 竖屏截图的宽高比
PHONE_TOP = 0.0083
DOC_PANE_U, DOC_PANE_V = 0.405, 0.909   # 剧本截图里右侧文档区（左边界 u，上边界 v）

random.seed(7)


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def qx(deg):
    return Quaternion((1, 0, 0), math.radians(deg))


# ---------------------------------------------------------------- 材质
def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    m.node_tree.nodes.clear()
    return m, m.node_tree.nodes, m.node_tree.links


def node(N, kind, **inputs):
    n = N.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def value(N, name, v):
    n = N.new("ShaderNodeValue")
    n.name = n.label = name
    n.outputs[0].default_value = v
    return n


def math_node(N, L, op, a, b, clamp=False):
    n = N.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, s in enumerate((a, b)):
        if isinstance(s, (int, float)):
            n.inputs[i].default_value = s
        else:
            L.new(s, n.inputs[i])
    return n.outputs[0]


def mix_rgb(N, L, fac, a, b):
    n = N.new("ShaderNodeMix")
    n.data_type = "RGBA"
    for idx, s in ((0, fac), (6, a), (7, b)):
        if isinstance(s, (int, float)):
            n.inputs[idx].default_value = s
        elif isinstance(s, tuple):
            n.inputs[idx].default_value = s
        else:
            L.new(s, n.inputs[idx])
    return n.outputs[2]


def felt_material(name, flat_hex):
    m, N, L = new_mat(name)
    out = N.new("ShaderNodeOutputMaterial")
    tc = N.new("ShaderNodeTexCoord")
    fib1 = node(N, "ShaderNodeTexNoise", Scale=900.0, Detail=8.0, Roughness=0.75)
    fib2 = node(N, "ShaderNodeTexNoise", Scale=2600.0, Detail=4.0, Roughness=0.8)
    blot = node(N, "ShaderNodeTexNoise", Scale=45.0, Detail=3.0)
    for t in (fib1, fib2, blot):
        L.new(tc.outputs["Object"], t.inputs["Vector"])
    height = math_node(N, L, "ADD", math_node(N, L, "MULTIPLY", fib2.outputs["Fac"], 0.6), fib1.outputs["Fac"])
    bump = node(N, "ShaderNodeBump", Strength=0.45, Distance=0.0004)
    L.new(height, bump.inputs["Height"])
    base = value(N, "BaseScale", BASE_SCALE)  # 取色后整体微调反照率用
    col = mix_rgb(N, L, math_node(N, L, "MULTIPLY", blot.outputs["Fac"], 0.35), lin(DISC_HEX),
                  tuple(min(1, c * 1.12) for c in lin(DISC_HEX)[:3]) + (1,))
    vs = N.new("ShaderNodeVectorMath")
    vs.operation = "SCALE"
    L.new(col, vs.inputs[0])
    L.new(base.outputs[0], vs.inputs["Scale"])
    bsdf = node(N, "ShaderNodeBsdfPrincipled", Roughness=1.0)
    bsdf.inputs["Sheen Weight"].default_value = 0.5
    bsdf.inputs["Sheen Roughness"].default_value = 0.45
    bsdf.inputs["Sheen Tint"].default_value = (1.0, 0.62, 0.45, 1.0)
    bsdf.inputs["Specular IOR Level"].default_value = 0.12
    L.new(vs.outputs[0], bsdf.inputs["Base Color"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    em = node(N, "ShaderNodeEmission", Color=lin(flat_hex), Strength=1.0)
    flat = value(N, "Flat", 0.0)
    mix = N.new("ShaderNodeMixShader")
    L.new(flat.outputs[0], mix.inputs[0])
    L.new(bsdf.outputs[0], mix.inputs[1])
    L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    return m


def simple_material(name, color, rough=0.5, metal=0.0, coat=0.0):
    m, N, L = new_mat(name)
    out = N.new("ShaderNodeOutputMaterial")
    b = node(N, "ShaderNodeBsdfPrincipled", Roughness=rough, Metallic=metal)
    b.inputs["Base Color"].default_value = color
    b.inputs["Coat Weight"].default_value = coat
    L.new(b.outputs[0], out.inputs["Surface"])
    return m


def desk_material():
    m, N, L = new_mat("Desk")
    out = N.new("ShaderNodeOutputMaterial")
    tc = N.new("ShaderNodeTexCoord")
    nz = node(N, "ShaderNodeTexNoise", Scale=180.0, Detail=6.0)
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    bump = node(N, "ShaderNodeBump", Strength=0.08, Distance=0.0005)
    L.new(nz.outputs["Fac"], bump.inputs["Height"])
    b = node(N, "ShaderNodeBsdfPrincipled", Roughness=0.95)
    b.inputs["Base Color"].default_value = (0.016, 0.014, 0.013, 1)
    b.inputs["Specular IOR Level"].default_value = 0.12
    L.new(bump.outputs["Normal"], b.inputs["Normal"])
    L.new(b.outputs[0], out.inputs["Surface"])
    return m


def glass_cover(N, L, emission_out, out):
    # 屏幕玻璃：自发光贴图 + 一点掠射反光
    gl = node(N, "ShaderNodeBsdfGlossy", Roughness=0.12)
    lw = node(N, "ShaderNodeLayerWeight", Blend=0.04)
    add = N.new("ShaderNodeMixShader")
    L.new(lw.outputs["Fresnel"], add.inputs[0])
    L.new(emission_out, add.inputs[1])
    L.new(gl.outputs[0], add.inputs[2])
    L.new(add.outputs[0], out.inputs["Surface"])


def load_img(path):
    img = bpy.data.images.load(path, check_existing=True)
    return img


def screen_material():
    m, N, L = new_mat("LaptopScreen")
    out = N.new("ShaderNodeOutputMaterial")
    uv = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(uv.outputs["UV"], sep.inputs[0])
    main = N.new("ShaderNodeTexImage")
    main.image = load_img(TEX_MAIN)
    main.interpolation = "Cubic"
    main.extension = "EXTEND"
    L.new(uv.outputs["UV"], main.inputs["Vector"])
    # 剧本文档：只有右侧文档区向上滚动
    scroll = value(N, "Scroll", 0.0)
    mask = math_node(N, L, "MULTIPLY",
                     math_node(N, L, "GREATER_THAN", sep.outputs[0], DOC_PANE_U),
                     math_node(N, L, "LESS_THAN", sep.outputs[1], DOC_PANE_V))
    v2 = math_node(N, L, "SUBTRACT", sep.outputs[1], math_node(N, L, "MULTIPLY", mask, scroll.outputs[0]))
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(sep.outputs[0], comb.inputs[0])
    L.new(v2, comb.inputs[1])
    doc = N.new("ShaderNodeTexImage")
    doc.image = load_img(TEX_DOC)
    doc.interpolation = "Cubic"
    doc.extension = "CLIP"
    L.new(comb.outputs[0], doc.inputs["Vector"])
    doc_col = mix_rgb(N, L, doc.outputs["Alpha"], (1, 1, 1, 1), doc.outputs["Color"])
    docmix = value(N, "DocMix", 0.0)
    col = mix_rgb(N, L, docmix.outputs[0], main.outputs["Color"], doc_col)
    dim = value(N, "Dim", 1.0)
    vs = N.new("ShaderNodeVectorMath")
    vs.operation = "SCALE"
    L.new(col, vs.inputs[0])
    L.new(dim.outputs[0], vs.inputs["Scale"])
    # 玻璃裂纹：以图标为中心的 Voronoi 边线，半径随时间外扩
    cx = math_node(N, L, "MULTIPLY", math_node(N, L, "SUBTRACT", sep.outputs[0], 0.5), SCREEN_ASPECT)
    cy = math_node(N, L, "SUBTRACT", sep.outputs[1], 0.5)
    cv = N.new("ShaderNodeCombineXYZ")
    L.new(cx, cv.inputs[0])
    L.new(cy, cv.inputs[1])
    vor = N.new("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "2D"
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 11.0
    L.new(cv.outputs[0], vor.inputs["Vector"])
    lines = math_node(N, L, "SUBTRACT", 1.0, math_node(N, L, "DIVIDE", vor.outputs["Distance"], 0.03), clamp=True)
    ln = N.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    L.new(cv.outputs[0], ln.inputs[0])
    crack_r = value(N, "CrackR", 0.0)
    radial = math_node(N, L, "DIVIDE", math_node(N, L, "SUBTRACT", crack_r.outputs[0], ln.outputs["Value"]), 0.04, clamp=True)
    amt = value(N, "CrackAmt", 0.0)
    crack = math_node(N, L, "MULTIPLY", math_node(N, L, "MULTIPLY", lines, radial), amt.outputs[0])
    final = mix_rgb(N, L, crack, vs.outputs[0], (1, 1, 1, 1))
    em = node(N, "ShaderNodeEmission", Strength=1.0)
    L.new(final, em.inputs["Color"])
    glass_cover(N, L, em.outputs[0], out)
    return m


def phone_material():
    m, N, L = new_mat("PhoneScreen")
    out = N.new("ShaderNodeOutputMaterial")
    uv = N.new("ShaderNodeTexCoord")
    img = N.new("ShaderNodeTexImage")
    img.image = load_img(PHONE["path"])
    img.interpolation = "Cubic"
    L.new(uv.outputs["UV"], img.inputs["Vector"])
    em = node(N, "ShaderNodeEmission", Strength=0.8)
    L.new(img.outputs["Color"], em.inputs["Color"])
    glass_cover(N, L, em.outputs[0], out)
    return m


def row_material(i):
    # 每行一层自发光遮罩：透明 + 同一张截图的加亮
    m, N, L = new_mat(f"Row{i}")
    out = N.new("ShaderNodeOutputMaterial")
    uv = N.new("ShaderNodeTexCoord")
    img = N.new("ShaderNodeTexImage")
    img.image = load_img(PHONE["path"])
    img.interpolation = "Cubic"
    L.new(uv.outputs["UV"], img.inputs["Vector"])
    tint = mix_rgb(N, L, 0.25, img.outputs["Color"], (1.0, 0.62, 0.35, 1))
    glow = value(N, "Glow", 0.0)
    em = N.new("ShaderNodeEmission")
    L.new(tint, em.inputs["Color"])
    L.new(glow.outputs[0], em.inputs["Strength"])
    tr = N.new("ShaderNodeBsdfTransparent")
    add = N.new("ShaderNodeAddShader")
    L.new(tr.outputs[0], add.inputs[0])
    L.new(em.outputs[0], add.inputs[1])
    L.new(add.outputs[0], out.inputs["Surface"])
    return m


def title_material():
    m, N, L = new_mat("Title")
    out = N.new("ShaderNodeOutputMaterial")
    tr = N.new("ShaderNodeBsdfTransparent")
    em = node(N, "ShaderNodeEmission", Color=(1, 1, 1, 1), Strength=1.0)
    a = value(N, "TitleA", 0.0)
    mix = N.new("ShaderNodeMixShader")
    L.new(a.outputs[0], mix.inputs[0])
    L.new(tr.outputs[0], mix.inputs[1])
    L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    return m


def shard_material():
    m, N, L = new_mat("Shard")
    out = N.new("ShaderNodeOutputMaterial")
    b = node(N, "ShaderNodeBsdfPrincipled", Roughness=0.03, IOR=1.5)
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Base Color"].default_value = (0.95, 0.97, 1.0, 1)
    L.new(b.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- 几何
def link(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def box(name, dims, loc, mat, bevel=0.002, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = dims
    bpy.ops.object.transform_apply(scale=True)
    bm = o.modifiers.new("Bevel", "BEVEL")
    bm.width, bm.segments, bm.harden_normals = bevel, 4, True
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
    return o


def quad(name, w, h, mat, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
    lay = me.uv_layers.new()
    for lp in me.loops:
        lay.data[lp.index].uv = uv[lp.vertex_index]
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))


def empty(name, loc=(0, 0, 0), parent=None):
    o = link(bpy.data.objects.new(name, None))
    o.location = loc
    o.empty_display_size = 0.02
    if parent:
        o.parent = parent
    return o


def area_light(name, loc, target, size, energy, color):
    ld = bpy.data.lights.new(name, "AREA")
    ld.size, ld.energy, ld.color = size, energy, color
    o = link(bpy.data.objects.new(name, ld))
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def cord_points():
    # 两个圈的毛毡绳：长幅摆线 x = a·u + b·sin u, z = b·cos(π+u) + z0，左右对称
    a, b, z0, umax = 0.115 * R, 0.37 * R, 0.13 * R, 2.2 * math.pi
    pts = []
    n = 360
    for i in range(n + 1):
        u = -umax + 2 * umax * i / n
        pts.append((a * u + b * math.sin(u), -T / 2 - 0.45 * TUBE, b * math.cos(math.pi + u) + z0))
    return pts


def build_disc():
    root = empty("DuetRoot")
    root.rotation_mode = "QUATERNION"
    roll = empty("DuetRoll", (0, 0, R), root)
    bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=R, depth=T, rotation=(math.pi / 2, 0, 0))
    disc = bpy.context.object
    disc.name = "DuetDisc"
    bpy.ops.object.transform_apply(rotation=True)
    bm = disc.modifiers.new("Bevel", "BEVEL")
    bm.width, bm.segments, bm.harden_normals = 0.0038, 6, True
    bpy.ops.object.shade_smooth()
    disc.data.materials.append(felt_material("FeltDisc", DISC_HEX))
    disc.parent = roll
    cu = bpy.data.curves.new("Cord", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth, cu.bevel_resolution, cu.use_fill_caps = TUBE, 6, True
    sp = cu.splines.new("POLY")
    pts = cord_points()
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1.0)
    cord = link(bpy.data.objects.new("DuetCord", cu))
    cord.data.materials.append(felt_material("FeltCord", CORD_ICON_HEX))
    cord.parent = roll
    return root, roll, disc, cord


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    sc = bpy.context.scene
    w = bpy.data.worlds.new("World")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.003, 0.003, 0.0035, 1)

    desk = quad("Desk", 4, 4, desk_material())
    metal = simple_material("SpaceGray", (0.055, 0.056, 0.06, 1), 0.38, 0.9)
    black = simple_material("BlackGlass", (0.004, 0.004, 0.005, 1), 0.08, 0.0, 1.0)
    keys = simple_material("KeyWell", (0.008, 0.008, 0.009, 1), 0.6)
    box("LaptopBase", (0.32, 0.22, 0.012), (0, 0, 0.006), metal, 0.003)
    kb = quad("Keyboard", 0.27, 0.10, keys)
    kb.location = (0, 0.035, 0.01205)
    tp = quad("Trackpad", 0.12, 0.07, simple_material("Trackpad", (0.05, 0.05, 0.055, 1), 0.3, 0.8))
    tp.location = (0, -0.065, 0.01205)
    lid = empty("LidPivot", (0, 0.11, 0.012))
    lid.rotation_euler = (LID_TILT, 0, 0)
    box("Lid", (0.32, 0.006, 0.205), (0, 0.003, 0.1025), metal, 0.002, lid)
    bez = quad("Bezel", 0.312, 0.198, black)
    bez.parent, bez.location, bez.rotation_euler = lid, (0, -0.0002, 0.103), (math.pi / 2, 0, 0)
    scr = quad("Screen", SCREEN_W, SCREEN_H, screen_material())
    scr.parent, scr.location, scr.rotation_euler = lid, (0, -0.0004, SCREEN_Z), (math.pi / 2, 0, 0)

    box("Phone", (PHONE_L + 0.008, PHONE_W + 0.0067, 0.008), (PHONE_C.x, PHONE_C.y, 0.004), black, 0.003)
    ps = quad("PhoneScreen", PHONE_W, PHONE_L, phone_material())
    ps.location, ps.rotation_euler = (PHONE_C.x, PHONE_C.y, 0.00805), (0, 0, math.pi / 2)
    rows_x = []
    for i, (top, bot) in enumerate(PHONE["rows"]):
        vt, vb = 1 - top / PHONE["h"], 1 - bot / PHONE["h"]
        ro = quad(f"RowGlow{i}", PHONE_W, (vt - vb) * PHONE_L, row_material(i), ((0, vb), (1, vb), (1, vt), (0, vt)))
        x = PHONE_C.x - ((vt + vb) / 2 - 0.5) * PHONE_L
        ro.location, ro.rotation_euler = (x, PHONE_C.y, 0.0082), (0, 0, math.pi / 2)
        rows_x.append(x)

    for name, loc, tgt, size, e, col in (
            ("KeyAmber", (-0.65, -0.30, 0.42), (0.08, 0.0, 0.05), 0.45, KEY_E, (1.0, 0.80, 0.58)),
            ("Rim", (0.45, 0.65, 0.30), (0.08, 0.0, 0.05), 0.35, 16.0, (0.85, 0.9, 1.0)),
            ("Fill", (0.15, -0.9, 0.25), (0.08, 0.0, 0.05), 0.8, 4.0, (1.0, 0.95, 0.9))):
        area_light(name, loc, tgt, size, e, col)

    root, roll, disc, cord = build_disc()

    # 标题：屏盖局部坐标，屏幕正中
    font = None
    for p in glob.glob("/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/PingFang.ttc") + \
            ["/System/Library/Fonts/Hiragino Sans GB.ttc"]:
        if os.path.exists(p):
            font = bpy.data.fonts.load(p, check_existing=True)
            break
    tc = bpy.data.curves.new("Title", "FONT")
    tc.body = "Claude Duet 实机演示"
    tc.align_x, tc.align_y = "CENTER", "CENTER"
    if font:
        tc.font = font
    title = link(bpy.data.objects.new("Title", tc))
    title.data.materials.append(title_material())
    title.parent, title.location, title.rotation_euler = lid, (0, -0.0010, SCREEN_Z), (math.pi / 2, 0, 0)
    bpy.context.view_layer.update()
    tc.size = 0.17 / max(title.dimensions.x, 1e-6)

    cam_t = empty("CamTarget")
    cd = bpy.data.cameras.new("Cam")
    cd.lens, cd.clip_start = 50, 0.01
    cd.dof.use_dof, cd.dof.focus_object, cd.dof.aperture_fstop = True, roll, 4.0
    cam = link(bpy.data.objects.new("Cam", cd))
    con = cam.constraints.new("TRACK_TO")
    con.target, con.track_axis, con.up_axis = cam_t, "TRACK_NEGATIVE_Z", "UP_Y"
    sc.camera = cam
    bpy.context.view_layer.update()
    return dict(sc=sc, lid=lid, root=root, roll=roll, disc=disc, cord=cord, cam=cam, cam_t=cam_t,
                title=title, rows_x=rows_x, font=font.filepath if font else None)


# ---------------------------------------------------------------- 动画
def animate(S):
    sc, lid = S["sc"], S["lid"]
    Ml = lid.matrix_world.copy()
    ql = Ml.to_quaternion()
    n = (Ml.to_3x3() @ Vector((0, -1, 0))).normalized()

    def scr(x, z, out):
        return Ml @ Vector((x, -0.0004 - out, z))

    C = scr(0, SCREEN_Z, 0.0015)
    rows_x = S["rows_x"]
    Lnd = Vector((0, -0.165, 0))
    H1 = Vector((0.19, -0.13, 0))
    PH = lambda x: Vector((x, PHONE_C.y, PHONE_TOP))
    D2 = Vector((0.19, -0.17, 0))
    OUT = T / 2 + 0.0015
    S1 = scr(0.06, SCREEN_Z + 0.045, OUT)
    S2 = scr(0.095, SCREEN_Z - 0.035, OUT)
    PF = scr(0.14, R - 0.005, OUT + 0.011)
    QF = Quaternion((0, 0, 1), math.radians(-17)) @ ql
    x_end = rows_x[-1] + 0.006
    up = Vector((0, 0, 1))

    def hop(a, b, h, s):
        return a.lerp(b, s) + up * (4 * h * s * (1 - s))

    def squash(t):
        if t < 0 or t > 10:
            return 1.0
        return 1 - 0.15 * math.sin(math.pi * t / 6) if t <= 6 else 1 + 0.04 * math.sin(math.pi * (t - 6) / 4)

    TH_PH = 4 * math.pi                       # 落到手机时的滚动角
    th_row_end = TH_PH + (x_end - rows_x[0]) / R
    th_s1 = th_row_end - 4 * math.pi
    DROP = (S1 - S2).length
    th_s2 = th_s1 - DROP / R
    th_f = 2 * math.pi * math.floor((th_s2 - 0.2) / (2 * math.pi)) + 0.2

    def state(f):
        """返回 (center 或 None, contact 或 None, quat, theta, (k, ky, sz), flat)"""
        if f < 60:
            return C, None, ql, 0.0, (ICON_K, 0.06, 1.0), 1.0
        if f < 75:
            s = (f - 60) / 15
            ctrl = C + n * 0.13 + up * 0.03
            c = C * (1 - s) ** 2 + ctrl * (2 * s * (1 - s)) + (Lnd + up * R) * s * s
            g = smooth(0, 0.35, s)
            return c, None, qx(-15 - 345 * s), 0.0, (ICON_K + (1 - ICON_K) * g, 0.06 + 0.94 * g, 1.0), 0.0
        if f < 120:
            t = f - 75
            tilt = 13 * math.exp(-t / 14) * math.sin(2 * math.pi * t / 20) * (1 - smooth(100, 118, f))
            return None, Lnd, qx(tilt), 0.0, (1, 1, squash(t)), 0.0
        if f < 127.5:
            s = (f - 120) / 7.5
            return None, hop(Lnd, H1, 0.045, s), qx(0), 2 * math.pi * s, (1, 1, 1), 0.0
        if f < 129.5:
            return None, H1, qx(0), 2 * math.pi, (1, 1, 1 - 0.14 * math.sin(math.pi * (f - 127.5) / 2)), 0.0
        if f < 135:
            s = (f - 129.5) / 5.5
            return None, hop(H1, PH(rows_x[0]), 0.04, s), qx(0), 2 * math.pi + 2 * math.pi * s, (1, 1, 1), 0.0
        if f < 240:
            if f <= 225:
                x = rows_x[0] + (rows_x[-1] - rows_x[0]) * (f - 135) / 90
            else:
                x = rows_x[-1] + 0.006 * math.sin(0.5 * math.pi * min(1, (f - 225) / 10))
            return None, PH(x), qx(0), TH_PH + (x - rows_x[0]) / R, (1, 1, squash(f - 135)), 0.0
        if f < 255:
            s = (f - 240) / 15
            return None, hop(PH(x_end), D2, 0.05, s), qx(0), th_row_end - 2 * math.pi * s, (1, 1, 1), 0.0
        if f < 257:
            return None, D2, qx(0), th_row_end - 2 * math.pi, (1, 1, squash((f - 255) * 3)), 0.0
        if f < 270:
            s = (f - 257) / 13
            c = (D2 + up * R).lerp(S1, s) + up * (4 * 0.05 * s * (1 - s))
            return c, None, Quaternion().slerp(ql, smooth(0, 1, s)), th_row_end - 2 * math.pi - 2 * math.pi * s, (1, 1, 1), 0.0
        if f < 345:
            e = smooth(270, 345, f)
            return S1.lerp(S2, e), None, ql, th_s1 - DROP * e / R, (1, 1, 1), 0.0
        if f < 360:
            s = smooth(345, 360, f)
            c = S2.lerp(PF, s) + n * (0.02 * math.sin(math.pi * s))
            return c, None, ql.slerp(QF, s), th_s2 + (th_f - th_s2) * s, (1, 1, 1), 0.0
        return PF, None, QF, th_f, (1, 1, 1), 0.0

    root, roll = S["root"], S["roll"]
    flat_nodes = [bpy.data.materials[m].node_tree.nodes["Flat"].outputs[0] for m in ("FeltDisc", "FeltCord")]
    prev = None
    centers = {}
    for f in range(FRAMES):
        center, contact, q, th, (k, ky, sz), flat = state(f)
        if prev is not None and q.dot(prev) < 0:
            q = -q
        prev = q.copy()
        sx = k / math.sqrt(sz)
        scale = Vector((sx, ky / math.sqrt(sz) if ky == 1 else ky, k * sz))
        if contact is None:
            contact = center - q.to_matrix() @ Vector((0, 0, R * scale.z))
        root.location, root.rotation_quaternion, root.scale = contact, q, scale
        roll.rotation_euler = (0, th, 0)
        for o, p in ((root, "location"), (root, "rotation_quaternion"), (root, "scale"), (roll, "rotation_euler")):
            o.keyframe_insert(p, frame=f)
        for s in flat_nodes:
            s.default_value = flat
            s.keyframe_insert("default_value", frame=f)
        centers[f] = contact + q.to_matrix() @ Vector((0, 0, R * scale.z))

    # 屏幕材质的关键帧
    sn = bpy.data.materials["LaptopScreen"].node_tree.nodes

    def keys(sock, pts):
        for f, v in pts:
            sock.default_value = v
            sock.keyframe_insert("default_value", frame=f)

    # 不同位置受光差很多：按段微调毛毡反照率，让受光面始终接近 #D0744E（按取色结果标定）
    for m in ("FeltDisc", "FeltCord"):
        keys(bpy.data.materials[m].node_tree.nodes["BaseScale"].outputs[0],
             [(120, BASE_SCALE), (135, 1.25 * BASE_SCALE), (238, 1.25 * BASE_SCALE), (257, BASE_SCALE),
              (266, 0.65 * BASE_SCALE), (345, 0.7 * BASE_SCALE), (362, 0.58 * BASE_SCALE)])
    keys(sn["CrackR"].outputs[0], [(59, 0.0), (60, 0.06), (63, 0.24), (70, 0.30)])
    keys(sn["CrackAmt"].outputs[0], [(59, 0.0), (60, 1.0), (200, 0.9), (245, 0.0)])
    keys(sn["DocMix"].outputs[0], [(255, 0.0), (275, 1.0)])
    keys(sn["Scroll"].outputs[0], [(275, 0.0), (300, 0.03), (330, 0.14), (345, 0.17)])
    keys(sn["Dim"].outputs[0], [(360, 1.0), (376, 0.05)])
    keys(bpy.data.materials["Title"].node_tree.nodes["TitleA"].outputs[0], [(370, 0.0), (386, 1.0)])
    for i in range(7):
        fk = 135 + 15 * i
        keys(bpy.data.materials[f"Row{i}"].node_tree.nodes["Glow"].outputs[0],
             [(fk - 4, 0.0), (fk + 1, 1.1), (fk + 10, 0.45), (250, 0.45), (262, 0.0)])

    build_shards(S, Ml, n)

    # 相机：关键位置 + Catmull-Rom 平滑
    xm = (rows_x[0] + rows_x[-1]) / 2
    cam_keys = [
        (0, (0.0, -0.60, 0.075), C),
        (60, (0.0, -0.37, 0.085), C),
        (78, (0.0, -0.47, 0.070), Vector((0, -0.03, 0.068))),
        (120, (0.05, -0.50, 0.075), Vector((0.06, -0.07, 0.05))),
        (128, (0.15, -0.46, 0.085), Vector((0.17, -0.09, 0.06))),
        (135, (0.20, -0.42, 0.090), Vector((rows_x[0], -0.035, 0.035))),
        (180, (xm - 0.03, -0.36, 0.100), Vector((xm, -0.035, 0.03))),
        (225, (rows_x[-1] - 0.02, -0.32, 0.12), Vector((rows_x[-1], -0.035, 0.025))),
        (240, (xm - 0.03, -0.25, 0.17), Vector((xm - 0.005, -0.035, 0.01))),
        (256, (0.22, -0.52, 0.11), Vector((0.15, -0.04, 0.07))),
        (264, (0.12, -0.56, 0.13), Vector((0.09, 0.04, 0.13))),
        (272, (0.08, -0.50, 0.12), Vector((0.07, 0.11, 0.13))),
        (345, (0.09, -0.45, 0.10), Vector((0.09, 0.11, 0.10))),
        (362, (0.055, -0.48, 0.095), Vector((0.055, 0.11, 0.09))),
        (449, (0.065, -0.68, 0.110), Vector((0.065, 0.10, 0.095))),
    ]
    cam_keys = [(f, Vector(p), Vector(t)) for f, p, t in cam_keys]

    def cr(i, f, idx):
        P = [k[idx] for k in cam_keys]
        F = [k[0] for k in cam_keys]
        f0, f1 = F[i], F[i + 1]
        s = (f - f0) / (f1 - f0)
        p0, p1 = P[i], P[i + 1]
        m0 = (P[i + 1] - P[i - 1]) / (F[i + 1] - F[i - 1]) * (f1 - f0) if i > 0 else (p1 - p0)
        m1 = (P[i + 2] - P[i]) / (F[i + 2] - F[i]) * (f1 - f0) if i + 2 < len(P) else (p1 - p0)
        h = (2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2)
        return p0 * h[0] + m0 * h[1] + p1 * h[2] + m1 * h[3]

    cam, tgt = S["cam"], S["cam_t"]
    for f in range(FRAMES):
        i = max(j for j in range(len(cam_keys) - 1) if cam_keys[j][0] <= f)
        cam.location = cr(i, f, 1)
        tgt.location = cr(i, f, 2)
        cam.keyframe_insert("location", frame=f)
        tgt.keyframe_insert("location", frame=f)
    S["centers"] = centers


def build_shards(S, Ml, n):
    mat = shard_material()
    rings = [(0.003, 0.013, 5), (0.013, 0.025, 7), (0.025, 0.037, 9), (0.037, 0.048, 11)]
    g = Vector((0, 0, -2.2))
    for ri, (r0, r1, cnt) in enumerate(rings):
        off = random.random()
        for j in range(cnt):
            a0 = (j + off + random.uniform(-0.15, 0.15)) / cnt * 2 * math.pi
            a1 = (j + 1 + off + random.uniform(-0.15, 0.15)) / cnt * 2 * math.pi
            rr0, rr1 = r0 * random.uniform(0.9, 1.1), r1 * random.uniform(0.9, 1.1)
            pts2 = [(rr0 * math.cos(a0), rr0 * math.sin(a0)), (rr1 * math.cos(a0), rr1 * math.sin(a0)),
                    (rr1 * math.cos(a1), rr1 * math.sin(a1)), (rr0 * math.cos(a1), rr0 * math.sin(a1))]
            cx = sum(p[0] for p in pts2) / 4
            cz = sum(p[1] for p in pts2) / 4
            th = 0.0009
            verts = [(x - cx, yy, z - cz) for yy in (-th, th) for x, z in pts2]
            faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
            me = bpy.data.meshes.new(f"Shard{ri}_{j}")
            me.from_pydata(verts, [], faces)
            me.materials.append(mat)
            o = link(bpy.data.objects.new(me.name, me))
            o.rotation_mode = "QUATERNION"
            p0 = Ml @ Vector((cx, -0.0016, SCREEN_Z + cz))
            q0 = Ml.to_quaternion()
            radial = (Ml.to_3x3() @ Vector((cx, 0, cz))).normalized()
            v = radial * random.uniform(0.25, 0.55) * (1 + (r0 / 0.03)) + n * random.uniform(0.25, 0.6)
            axis = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()
            w = random.uniform(6, 14)
            for f in range(59, 89):
                t = max(0.0, (f - 60) / FPS)
                o.location = p0 + v * t + g * (0.5 * t * t)
                o.rotation_quaternion = Quaternion(axis, w * t) @ q0
                o.hide_render = not (60 <= f <= 86)
                o.hide_viewport = o.hide_render
                for p in ("location", "rotation_quaternion", "hide_render", "hide_viewport"):
                    o.keyframe_insert(p, frame=f)
            # 59 之前与 86 之后保持隐藏（常量外推）
            o.hide_render = True
            o.keyframe_insert("hide_render", frame=0)
            o.hide_viewport = True
            o.keyframe_insert("hide_viewport", frame=0)


# ---------------------------------------------------------------- 渲染
def setup_render(sc, samples, pct):
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type != "CPU"
    sc.cycles.device = "GPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces, sc.cycles.transmission_bounces = 8, 10
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, pct
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 0, FRAMES - 1
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"


def render_still(sc, f, path):
    sc.frame_set(f)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def sample_point(S, f):
    sc = S["sc"]
    sc.frame_set(f)
    root = S["root"]
    # 圆片正面左下方（避开绳子），用不滚动的 root 坐标系
    p = root.matrix_world @ Vector((-0.40 * R, -T / 2 - 0.0006, R - 0.60 * R))
    v = world_to_camera_view(sc, S["cam"], p)
    W, H = sc.render.resolution_x * sc.render.resolution_percentage / 100, sc.render.resolution_y * sc.render.resolution_percentage / 100
    ok = 0 < v.x < 1 and 0 < v.y < 1 and v.z > 0 and f >= 61
    return dict(frame=f, visible=ok, x=round(v.x * W), y=round((1 - v.y) * H))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["build"]
    mode = argv[0]
    S = build_scene()
    animate(S)
    sc = S["sc"]
    os.makedirs(CHECK, exist_ok=True)
    print("FONT", S["font"], "ROWS_X", [round(x, 4) for x in S["rows_x"]])
    if mode == "build":
        setup_render(sc, 64, 50)
    elif mode == "textures":
        setup_render(sc, 64, 100)
        cd = bpy.data.cameras.new("TexCam")
        cd.lens = 50
        tc = link(bpy.data.objects.new("TexCam", cd))
        Ml = S["lid"].matrix_world
        n = (Ml.to_3x3() @ Vector((0, -1, 0))).normalized()
        C = Ml @ Vector((0, 0, SCREEN_Z))
        tc.location = C + n * 0.36
        tc.rotation_euler = (C - tc.location).to_track_quat("-Z", "Y").to_euler()
        sc.camera = tc
        render_still(sc, 30, os.path.join(CHECK, "tex_1_laptop_main.png"))
        for o in (S["disc"], S["cord"]):
            o.hide_render = True
        render_still(sc, 300, os.path.join(CHECK, "tex_2_laptop_doc.png"))
        cd2 = bpy.data.cameras.new("PhoneCam")
        cd2.type, cd2.ortho_scale = "ORTHO", 0.2
        pc = link(bpy.data.objects.new("PhoneCam", cd2))
        pc.location, pc.rotation_euler = (PHONE_C.x, PHONE_C.y, 0.3), (0, 0, math.pi / 2)
        sc.camera = pc
        render_still(sc, 238, os.path.join(CHECK, "tex_3_phone.png"))
        return
    elif mode == "check":
        setup_render(sc, 64, 50)
        pts = []
        for f in (0, 60, 90, 150, 270, 400):
            render_still(sc, f, os.path.join(CHECK, "contact", f"c_{f:04d}.png"))
        for i in range(18):
            f = round(i * (FRAMES - 1) / 17)
            render_still(sc, f, os.path.join(CHECK, "stills", f"s{i:02d}_f{f:04d}.png"))
            pts.append(sample_point(S, f))
        json.dump(pts, open(os.path.join(CHECK, "sample_points.json"), "w"), indent=1)
    elif mode == "probe":
        setup_render(sc, 48, 50)
        pts = []
        for f in map(int, argv[1].split(",")):
            render_still(sc, f, os.path.join(CHECK, "probe", f"p_f{f:04d}.png"))
            pts.append(sample_point(S, f))
        json.dump(pts, open(os.path.join(CHECK, "probe_points.json"), "w"), indent=1)
        return
    elif mode == "full":
        setup_render(sc, 160, 100)
        sc.render.filepath = os.path.join(HERE, "frames", "f_")
        bpy.ops.render.render(animation=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "开头动效.blend"))


main()
