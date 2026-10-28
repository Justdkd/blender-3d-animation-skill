---
name: blender-3d-animation
description: 用 Blender Python 脚本在本机做短 3D 动画镜头（片头、产品动效、角色在电脑/手机屏幕间穿梭、Logo 演绎、真实截图做屏幕贴图），按“认素材 → 隐私打码 → 贴图检查 → 接触表 → 18 张静帧审片取色 → 修 → 全片渲染 + MP4”的固定流程交付。用户提到 Blender、3D 动画、3D 开头、3D 片头、毛毡/黏土/实物质感角色、Cycles 渲染、把截图放进 3D 电脑屏幕、角色破屏而出，或想要一段可脚本复现的 3D 镜头时都用本技能，即使没说“Blender”。不用于 2D 动效（HyperFrames）、实拍剪辑（剪映/video-use）或 AI 生成视频。
---

# Blender 3D 动画镜头

一段镜头 = 一个 Python 场景脚本 + 一个 `.blend` + PNG 序列 + H.264 MP4。脚本是唯一事实来源：改需求就改脚本、重跑，不在 Blender 界面里手调后忘了回写。

这套流程来自 2026-10-27 的「Claude Duet 实机演示」15 秒开头（`examples/claude-duet-opening/`）。每做一片，把新踩的坑补进 `references/pitfalls.md`，把仍未解决的写进仓库根目录的 `FOLLOWUPS.md`。

## 0. 先把需求整理成镜头表

从用户的描述里抽出这些，缺的只问真正影响画面的：

- **素材角色**：角色参考图、每块屏幕要显示的截图（电脑主界面、文档、手机消息……）。
- **主角**：形状、尺寸感、材质、主色 HEX（取色就对这个值）、运动方式（滚、跳、落地挤压）。
- **场景与灯光**：桌面、设备、主光方向和色温、轮廓光、景深、机位高度。
- **镜头表**：按帧写清每段做什么；有 BPM 就换算成帧（120 BPM、30 fps → 1 拍 = 15 帧），关键动作卡在拍点上。
- **规格**：分辨率、fps、总帧数、是否要留 9:16 中间裁切区（1920×1080 里中间 1080×1080）。
- **检查清单**：用户点名的检查项照抄，再补上第 6 步的默认项。

模板见 `references/brief-template.md`。

## 1. 认素材：按内容匹配，缺图就停

列出素材目录，逐张打开看内容，再决定每张图对应哪个角色，不按文件名猜。先向用户报告匹配结果。

缺了一块屏幕的截图，就停下告诉用户缺哪张，**不要自己编一个界面**：编出来的 UI 会被当成真产品画面发出去。素材内容对不上（比如要“7 行周计划”，给的是一段聊天），也照实说。用户明确说“占位就行”时，才用中性灰条占位，并在报告里写明是占位。

## 2. 隐私检查，然后裁切打码

每张截图都看一遍：名字、邮箱、头像、日期时间、通知、地址栏里的 ID、和本期无关的私事。逐项告诉用户看到了什么。素材本身写了“某类内容一律打码”的，照做。

用 `scripts/prep_screens.py` 一步完成打码和裁切（坐标是原图像素）：

```bash
python3 scripts/prep_screens.py 素材/main.png textures/main.png --top 168 \
  --mosaic 1264,774,990,164 --mosaic 14,1976,58,58
```

状态栏、浏览器标签栏和地址栏要裁掉。打码后用 Read 打开结果确认，再继续。保留公开的账号名（如频道名）、去掉真名，拿不准就问。

## 3. 写场景脚本

从 `examples/claude-duet-opening/duet_opening.py` 复制一份到本期输出目录，在它的结构上改，不要从零写。它已经解决了 Blender 5 的 API 坑和下面这些做法：

- **模式切换**：`-- build | textures | check | probe 90,185 | animatic | full`，同一个脚本覆盖所有检查和正式渲染。
- **屏幕 = 自发光贴图 + 色彩管理用 Standard**：emission 强度 1、view transform `Standard` 时，屏幕像素和截图一致；AgX/Filmic 会把截图洗灰。
- **角色层级**：`Root`（落点、朝向、挤压缩放）→ `Roll`（绕自身轴滚动）→ 网格。Root 原点放在接触点，挤压和摇晃都以地面为支点。
- **每帧烘焙**：用 `state(f)` 函数算每一帧的位置、四元数、滚动角、缩放，逐帧打关键帧（线性插值）。跳跃用抛物线，滚动角 = 距离 / 半径，所以不会打滑。四元数要和上一帧同号，否则会突然翻转。
- **英雄时刻对正**：落地、定格这些时刻，让滚动角落在 2π 的整数倍（或加一点歪头角度），图案正对镜头。
- **相机**：位置和看向点各一组关键点，用 Catmull-Rom 平滑插值；景深对焦物体设成 `Roll`。
- **主角单独一盏主光（Light Linking）**：场景主光排除主角，另一盏同色主光挂在 Root 上只照主角，主角走到哪里受光都一样，不要按段调反照率去补。做法见 `hero_light()` 和 pitfalls。
- **主角别挡住要看的东西**：立着的主角会挡住身后的内容。逐行点亮这类镜头，让主角走在远离镜头的一侧（例子里的 `ROLL_Y`）。
- **材质参数做成 Value 节点**（`Flat`、`DocMix`、`Scroll`、`CrackR`、`Glow`、`TitleA`），这样能直接打关键帧。
- **毛毡质感**：Principled + Sheen + 两层细 Noise 凹凸 + 低频色斑，不用粒子毛发（渲染慢、难控）。
- **列表逐行点亮**：每行一个透明叠加面片，UV 指向同一张截图的那一行，叠加发光强度按拍点打关键帧。
- **CJK 标题**：PingFang 在 `/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/PingFang.ttc`，找不到就退到 `/System/Library/Fonts/Hiragino Sans GB.ttc`。标题按目标宽度自动算字号，放在屏幕局部坐标里，保证完整落在屏幕内。

改动集中在：顶部常量（尺寸、颜色、贴图路径）、`build_scene()` 里的道具、`animate()` 里的 `state(f)` 和 `cam_keys`。

## 4. 贴图检查（动画之前）

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P 脚本.py -- textures
```

每块屏幕正面渲一张，打开看：清不清楚、有没有拉伸、打码是否还在、方向对不对。首次渲染要先编译 GPU 内核，M5 Pro 上约 2 分钟，之后每张几秒。

## 5. 检查渲染：接触表 + 18 张半分辨率静帧

`-- check` 模式渲用户点名的接触表帧，再在全片均匀取 18 帧（`round(i*(N-1)/17)`），50% 分辨率、低采样，同时写出取色点 `check/sample_points.json`。拼图：

```bash
scripts/sheet.sh 'check/stills/s*.png' 3 check/stills_sheet.png
scripts/sheet.sh --phone 'check/stills/s*.png' check/phone_sheet.png
scripts/sheet.sh --strip 脚本.py 120 check/strip_f0120.png
```

`--phone` 每格缩到 360 px 宽，3 列。`--strip` 先用该脚本的 `-- probe` 渲出起始帧开始的连续 12 帧，再拼 6×2。跳跃、破屏这类最快的动作，各出一条 12 连帧。

## 6. 逐帧越界检查 + 逐张审片，列问题（按帧号）

先跑越界检查。静帧只抽了 18 帧，出画、出 9:16 区这类问题人眼会漏；这个脚本把物体逐帧投影到画面，全片几秒钟跑完：

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup 镜头.blend \
  -P scripts/bounds_check.py -- --check 主角网格,主角绳子 --check 标题@370 \
  --inside 标题:屏幕 --safe 420,1500 --out check/bounds.json
```

输出“出画 / 出 9:16 区 / 超出 屏幕”的帧号区间，`bounds.json` 里有每帧的像素包围框，照着改相机关键点。改完重跑，直到 `BOUNDS OK`（不用渲染，`-- build` 存好 .blend 就能查）。

再逐张看 stills_sheet，对每一项给出“通过/不通过 + 帧号”：

1. **主角颜色**：`python3 scripts/sample_color.py --points check/sample_points.json --dir check/stills --target D0744E`。自动取色点可能落在绳子、高光或阴影里，异常值要放大看一眼，必要时用 `--at png x y` 在干净的受光面重取。报告时写清哪些是取色点落错位置。
2. **图案朝向**：英雄时刻（落地、定格）图案正对镜头。
3. **屏幕清晰可读**：对焦、景深、反光不能吃掉内容。
4. **按节拍发生的事件**（逐行点亮等）按顺序、在拍点上。
5. **标题**完整在屏幕内，字体对。
6. **构图**：以 `bounds_check.py` 的结果为准；静帧上再看主角有没有挡住这一刻要看的内容。
7. **没有多余物体、Logo、文字**。

问题按帧号列给用户，修完先用 `-- probe 帧号,帧号` 只重渲受影响的帧确认，再进下一步。不要跳过这一步直接渲全片：全片一次一小时左右，返工代价大。

7 项检查之后，再按 1–10 打分：开头 2 秒抓不抓人、手机上看清不清楚（见 §6 手机测试）、运动质感、画面变化（每 2–4 秒有新东西）、节拍对位、品牌 / 主角准确。只看渲出来的帧，不按“本来想做的”打分。列出最差 3 处：帧号、证据（哪张图）、局部修法。只修这 3 处，用 `-- probe` 重渲，再打一轮分。每项 ≥ 8 才进第 7 步全片渲染。分数和问题写进 `check/review.md`。

## 低清预览

`-- animatic` 用 Workbench 或 EEVEE 渲染引擎、50% 分辨率、无运动模糊，渲全片后合成 MP4（带占位节拍音更好），给 dkd 看节奏，确认后再渲全片。耗时【待实测】。

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P 脚本.py -- animatic
```

成片在脚本旁边的 `check/animatic.mp4`。

## 7. 全片渲染

用 `scripts/render_full.sh`，配合 Bash 的 `run_in_background`：它会顺手开 `caffeinate`，渲完自动合成 H.264（yuv420p、crf 16、faststart）。脚本路径要写绝对路径。场景脚本的 full 模式要设 `use_overwrite=False` + `use_placeholder=True`（例子已设）：中途睡眠、崩溃或被打断，原样再跑同一条命令就从断点续渲，已渲好的帧跳过。

```bash
scripts/render_full.sh /绝对路径/脚本.py /绝对路径/输出目录 成片.mp4
```

参考耗时：M5 Pro、1080p、160 采样 + OIDN 降噪、带运动模糊，约 10 秒一帧，450 帧约 64 分钟。告诉用户大概几点渲完，并提醒：电脑别睡眠、别合盖、别关 Claude 窗口；渲染本身不需要联网。

渲完用 `scripts/sheet.sh --video` 从 MP4 抽 6–9 帧再看一遍，确认帧数、时长、分辨率（ffprobe）。

## 8. 汇报

- 取色结果（每帧 HEX 对目标，标明哪些是取色点落错）。
- 越界检查结果（`BOUNDS OK` 或剩下的帧号）。
- 每一项不通过的检查：帧号、原因、改了什么。补偿性做法要直说是补偿。
- 与需求不一致的地方：占位素材、素材分辨率不足、为了运动合理而改的造型。
- 打了码的内容和保留未打码的内容。
- 输出路径：脚本、`.blend`、PNG 序列、MP4、check 目录。
- 未提交 git。

## 参考

- `references/pitfalls.md`：Blender 5 API、色彩、光照、取色、渲染时间的坑，写脚本前读一遍。
- `references/brief-template.md`：需求模板。
- `examples/claude-duet-opening/`：完整可跑的例子和当时的需求。
