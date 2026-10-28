# 已踩过的坑

每条写：现象 → 原因 → 做法。新坑加在对应小节末尾，注明日期和出处那一期。

## Blender 5 Python API

- **`ShaderNodeMixRGB` 不要用**：5.x 用 `ShaderNodeMix` + `data_type="RGBA"`，输入按下标取：0 = Factor，6 = A 颜色，7 = B 颜色；输出 2 = 结果颜色。按名字取会撞上同名的 float/vector 插口。
- **`Material.use_nodes` / `World.use_nodes` 已弃用**：赋值会报 DeprecationWarning（6.0 会移除），用 `try` 包起来即可，节点树始终存在。
- **Math 节点辅助函数别塞三个操作数**：`MULTIPLY_ADD` 要三个输入，自己写的 `math_node(a, b, clamp)` 会把第三个参数当成 `use_clamp`，报 `expected True/False ... not NodeSocketFloat`。拆成两个节点。（2026-10-27 Duet）
- **关键帧默认插值**：先设 `preferences.edit.keyframe_new_interpolation_type = "LINEAR"` 再逐帧打关键帧，不必去碰 5.x 分层 action 的 fcurves。
- **隐藏切换要打关键帧**：`hide_render` / `hide_viewport` 在第 0 帧也打一个 True，否则外推会让碎片在开场就出现。
- **`.ttc` 字体**：`bpy.data.fonts.load` 只取第一个字面，PingFang.ttc 第一个是常规体，够用；要粗体得另找单字重文件。

## 颜色与色彩管理

- **屏幕截图必须 Standard**：view transform 用 `Standard`、look `None`，emission 强度 1，屏幕像素才和截图一致。
- **琥珀主光会把主角推黄推亮**：第一轮主光 55 W 时，受光面取到 #FF8A50–#FFCA72（目标 #D0744E）。降到 22 W、光色从 (1, .70, .42) 改成 (1, .80, .58)，Sheen 从 1.0 降到 0.5，地面段就对上了。
- **同一盏灯，不同位置受光差很多**：主角贴在后仰 15° 的屏幕上时迎着主光，亮了约 40%；在手机上又偏暗。当时的做法是按段给反照率打关键帧（手机段 ×1.25，屏幕段 ×0.65，定格段 ×0.58）。这是补偿，不是物理打光，汇报时要说明。（2026-10-27 Duet）
  **0.2.0 起改用 Light Linking**：场景主光的 `light_linking.receiver_collection` 设成一个只含主角、状态 `EXCLUDE` 的集合；另建一盏同色同尺寸的 `HeroKey`，用 Child Of 约束挂在 Root 上（关掉缩放，落地挤压不带动灯），receiver 设成只含主角、状态 `INCLUDE` 的集合。主角的影子仍由场景主光投在桌面上（receiver 不影响投影）。同一个集合不能既 INCLUDE 又 EXCLUDE，要建两个。不调任何反照率，18 帧取色落在 #CA6940–#E2784C。

## 取色

- **自动取色点会落在绳子/凸起图案上**：主角滚动后，固定在 Root 坐标系的取色点可能正好压在图案、它的阴影或高光上，读数偏差 30 以上。异常值放大看，再用 `sample_color.py --at` 在干净受光面重取。
- **取色范围用 6×6 均值**，单像素会被毛毡噪点带偏。

## 构图与镜头

- **主角离镜头太近会出画**：跳跃最高点、贴近屏幕时最容易出画。镜头表里每个跳跃单独加一个相机关键点看向弧顶。
- **9:16 裁切**：1920×1080 里中间 1080 是 x 420–1500。定格时“标题 + 主角”整体要落在这里，最后一段相机看向点往主角那侧偏一点。
- **低机位 + 光滑桌面 = 大片高光条**：桌面 roughness ≥ 0.95、Specular IOR Level ≈ 0.12 才像哑光。
- **手机屏玻璃反光会吃掉内容**：Layer Weight Blend 0.04 左右；俯视推镜时尤其明显。
- **人眼审 18 张静帧会漏越界**：v1 交付后用 `bounds_check.py` 复查，查出 75–84、229–257 帧圆片有一截出画，370–393 帧标题超出 9:16 区，静帧都没抽到这些帧。逐帧投影几秒就跑完，每次改相机后都跑。（2026-10-27 Duet）
- **立着的主角会挡住它压着的那一行**：低机位时，主角背后的东西全被挡住。让主角走在列表远离镜头的一侧，前面的大半行就露出来了；相机看向点放在主角和亮行之间，机位略抬高。（2026-10-27 Duet）

## 素材

- **ffmpeg overlay 默认输出 yuv420**：打码后再裁切会把奇数尺寸变成偶数，丢 1 像素。overlay 加 `format=rgb`（`prep_screens.py` 已处理）。
- **用户贴进对话的截图是压缩过的**（例如 2000 px 宽 webp），清晰度比原始截图低，需要清晰时请用户给原图文件。

## 渲染

- **首次渲染要编译 Metal 内核**：约 2 分钟，之后每张几秒。贴图检查那步顺便把内核编好。
- **耗时**：M5 Pro、1080p、160 spp + OIDN、运动模糊 0.5：约 10 秒/帧；50%、48–64 spp 的检查帧约 3–5 秒/帧。
- **睡眠会暂停渲染**：`caffeinate -i -s -w <blender pid>`，合盖仍会睡。
- **断点续渲**：full 模式设 `render.use_overwrite=False` + `use_placeholder=True`。中断后会留下 0 字节占位帧，不删就会被当成已渲好跳过；`render_full.sh` 启动前会删掉小于 2 KB 的帧，渲完再查一遍。
- **低清预览耗时**：`-- animatic` 用 Workbench 或 EEVEE、50% 分辨率、无运动模糊，渲全片后合成 MP4。耗时【待实测】。
