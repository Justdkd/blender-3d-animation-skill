# 当时的需求（2026-10-27，原文，路径换成占位）

Build a 15-second 3D opening shot in Blender with a Python script. Render a check pass first, review it, then the full shot.

PROJECT FOLDER
<项目目录>
All inputs are in its 素材/ subfolder. Put every output in 输出/开头动效/ (create it).

INPUTS (in 素材/)
- character.jpg: the hero character reference.
- The phone screenshot of the weekly workflow message (7 rows, Mon to Sun). List 素材/, open the images, and pick it by content, not by file name.
- Two laptop screenshots, if present: the Claude Duet web main screen, and the script document. Pick them by content too.
Before anything else, report which file you matched to each role. If either laptop screenshot is missing, stop and tell me which one to add; do not invent a UI.
Check every screenshot for personal details (names, email addresses, avatars, dates, other notifications) and tell me what you see before using it. Crop status bars and browser address bars off.

BRAND
HERO: "Duet", a felt disc. Match character.jpg: a thick round disc of terracotta wool felt, base color #D0744E, shadow side about #C46A45, with a raised felt cord on its face that runs left to right and makes two loops. No face, arms, legs or text. Build the felt look with a fuzzy shader and fine noise bump, not particle hair. It moves by rolling on its edge and hopping, with a slight squash on each landing.
SCENE: dark matte desk, warm amber key light from the left, soft rim light, shallow depth of field, low camera close to the desk surface. A laptop open with the screen tilted back, and a phone lying flat, screen up, to its right. Screens are emissive image textures, pixel-faithful to the screenshots. No other logos, brands or text in frame.

SHOTS (120 BPM, 1 beat = 15 frames)
- 0-60: fade up. Laptop shows the main-screen screenshot with a small flat 2D icon of the character centered on the screen. Slow push-in.
- 60: on the beat, the screen glass cracks outward from the icon and shards fly. The icon pops out as the 3D felt disc, lands upright on the desk, wobbles twice and settles by frame 120.
- 120-240: it hops twice onto the phone, then rolls along the message rows of the weekly workflow screenshot. Each row brightens as it passes, one row per beat (an emissive mask per row). Camera tracks low beside it, then pushes toward the phone screen.
- 240-360: it hops back to the laptop. The laptop texture crossfades to the script-document screenshot. It rolls down the screen while the document texture scrolls up.
- 360-450: it stops, leaning half out from the screen edge. Camera pulls back. The laptop screen shows the title "Claude Duet 实机演示" in clean white type, using a CJK font installed on this Mac (for example PingFang SC), fully inside the screen. Hold to the end.

FORMAT
Blender 5 Python script, Cycles on the GPU this Mac has, 1920x1080, 30 fps, 450 frames (15.0 s). Keep the action inside the center 1080x1080 so a 9:16 crop works later. Save the script, the .blend, a PNG sequence and an H.264 MP4 into 输出/开头动效/. No audio.

CHECKS
1. Before animating, render the three screen textures on their objects, plus a contact sheet of frames 0, 60, 90, 150, 270 and 400.
2. Render 18 stills at half resolution, evenly spaced across the timeline. Review each one: sample the disc's lit base color and report the RGB against #D0744E; the two loops face the camera in the hero moments; screens are sharp and readable; rows light up in order; the title sits fully inside the screen; no extra objects, logos or text.
3. List what is off by frame number, fix it, and only then render all 450 frames.

Report back: the sampled color, each check that failed and what you changed, and the output paths.
