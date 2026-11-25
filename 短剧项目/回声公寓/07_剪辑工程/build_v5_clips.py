"""
EP01 精剪 v5 — 自查后重剪
真实素材驱动，不靠子员工猜画面。
构建：带音轨完整成片。
"""
import subprocess, os, json, shutil

ROOT = r"D:\Hermes环境准备\AI漫剧制作\短剧项目\回声公寓"
SRC = os.path.join(ROOT, "06_视频素材")
AUD = os.path.join(ROOT, "05_配音与音效", "EP01_v2_Serena_去电音")
OUT = os.path.join(ROOT, "07_剪辑工程")
TMP = os.path.join(OUT, "tmp_v5")
os.makedirs(TMP, exist_ok=True)
os.makedirs(os.path.join(TMP, "clips"), exist_ok=True)

def ff(cmd):
    """运行 ffmpeg，失败抛异常"""
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("CMD:", " ".join(cmd[:5]), "...")
        print("ERR:", r.stderr[-2000:])
        raise RuntimeError("ffmpeg failed")
    return r

# ============================================================
# 第一步：裁好每个镜头片段（统一 24fps + 统一调色 + deshake）
# ============================================================
# 统一调色：走廊冷蓝（-色温 -10 +亮度 -5%），门内暖黄（+色温 +10 +亮度 -3%）
# 悬疑风格：饱和度 -20%，对比度 +10%，暗部加深
color_corridor = (
    "eq=brightness=-0.03:contrast=1.1:saturation=0.8,"
    "colorbalance=rs=-0.05:gs=-0.05:bs=0.08"
)
color_inside = (
    "eq=brightness=-0.02:contrast=1.1:saturation=0.85,"
    "colorbalance=rs=0.08:gs=0.03:bs=-0.05"
)

# 逐镜定义：入点/出点/调色/描述
# 基于真实抽帧结果，入出点都在有画面的安全区间内
shots = [
    # —— 开场蒙太奇（5 个镜头 + 1 个黑屏 = 6s）——
    {"id": "A1", "src": "S15", "start": 5.0, "end": 6.0,
     "color": color_corridor,
     "note": "S15 5-6s 惊恐脸近景（最炸镜头当第一帧），0.3s fade in"},
    {"id": "A2", "src": "S15", "start": 6.5, "end": 7.0,
     "color": color_corridor,
     "note": "S15 6.5-7s 更紧的惊恐脸，硬切"},
    {"id": "A3", "src": "S13", "start": 2.0, "end": 2.5,
     "color": color_inside,
     "note": "S13 2-2.5s 黑袍人正面近景（门内另一个自己），硬切"},
    {"id": "A4", "src": "S03", "start": 4.0, "end": 5.5,
     "color": color_corridor,
     "note": "S03 4-5.5s 门缝暖光推近感，1.1x 加速，0.2s 叠化进入"},
    {"id": "A5", "src": "S04", "start": 8.0, "end": 9.0,
     "color": color_corridor,
     "note": "S04 8-9s 最暗的门内深处，fade to black"},
    # A6 黑屏在第二步处理

    # —— 正常叙事（从第6秒开始）——
    {"id": "S02", "src": "S02", "start": 5.0, "end": 8.5,
     "color": color_corridor,
     "note": "林晚站 302 门前，揉头→拿水杯，3.5s"},
    {"id": "S03", "src": "S03", "start": 1.5, "end": 5.5,
     "color": color_corridor,
     "note": "停步门前，发现门缝光，4s"},
    {"id": "S04", "src": "S04", "start": 0.5, "end": 4.5,
     "color": color_corridor,
     "note": "凑近门缝往里看，4s"},
    {"id": "S05", "src": "S05", "start": 0.5, "end": 7.5,
     "color": color_inside,
     "note": "门内黑袍人侧身站立，7s（第一奇观）"},
    {"id": "S07", "src": "S07", "start": 0.5, "end": 6.0,
     "color": color_corridor,
     "note": "后退半步 + 水洒地，5.5s（恐惧外化）"},
    {"id": "S08", "src": "S08", "start": 0.5, "end": 4.0,
     "color": color_corridor,
     "note": "掏手机照亮，3.5s"},
    {"id": "S09", "src": "S09", "start": 0.5, "end": 7.0,
     "color": color_inside,
     "note": "伸手碰门内，镜像同步，6.5s（第二奇观）"},
    {"id": "S10", "src": "S10", "start": 0.5, "end": 8.0,
     "color": color_corridor,
     "note": "回声问答对峙，7.5s"},
    {"id": "S11", "src": "S11", "start": 0.5, "end": 4.5,
     "color": color_corridor,
     "note": "崩溃拍门，4s（情绪最高点）"},
    {"id": "S12", "src": "S12", "start": 4.5, "end": 8.5,
     "color": color_inside,
     "note": "门自行打开，4s"},
    {"id": "S13", "src": "S13", "start": 0.5, "end": 4.5,
     "color": color_inside,
     "note": "双人面对面，4s（第三奇观）"},
    {"id": "S14", "src": "S14", "start": 0.5, "end": 3.0,
     "color": color_corridor,
     "note": "夺门而逃，拖鞋掉落，2.5s"},
    {"id": "S15", "src": "S15", "start": 3.0, "end": 7.5,
     "color": color_corridor,
     "note": "僵住回头惊恐脸，4.5s + 末帧定格（结尾钩子）"},
]

# 裁剪每个片段
print("=== 裁剪片段 ===")
clip_files = {}
for s in shots:
    outp = os.path.join(TMP, "clips", f"{s['id']}_clip.mp4")
    clip_files[s["id"]] = outp
    if os.path.exists(outp):
        print(f"  {s['id']}: 已存在，跳过")
        continue
    vf = f"{s['color']},fps=24,scale=720:1280:flags=lanczos,crop=704:1248:8:16,scale=720:1280"
    srcp = os.path.join(SRC, f"EP01_{s['src']}.mp4")
    ff(["ffmpeg", "-y", "-ss", str(s["start"]), "-to", str(s["end"]),
        "-i", srcp, "-vf", vf, "-an",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", outp])
    dur = s["end"] - s["start"]
    print(f"  {s['id']}: {dur:.1f}s  →  {outp}")

# 开场蒙太奇的速度微调（A4 1.1x 加速）
print("\n=== 蒙太奇速度微调 ===")
a4_orig = clip_files["A4"]
a4_fast = os.path.join(TMP, "clips", "A4_clip_fast.mp4")
if not os.path.exists(a4_fast):
    ff(["ffmpeg", "-y", "-i", a4_orig, "-filter:v", "setpts=PTS/1.1",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", a4_fast])
    print("  A4 加速 1.1x 完成")
else:
    print("  A4 加速已存在")
clip_files["A4"] = a4_fast

# 黑屏 A6
a6_clip = os.path.join(TMP, "clips", "A6_clip.mp4")
if not os.path.exists(a6_clip):
    ff(["ffmpeg", "-y", "-f", "lavfi", "-i",
        "color=c=black:s=720x1280:d=1.5:r=24",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", a6_clip])
    print("  A6 黑屏 1.5s 完成")
clip_files["A6"] = a6_clip

# S15 结尾定格（取末帧，延长 1.5s + 缓慢推近）
s15_clip = clip_files["S15"]
s15_freeze = os.path.join(TMP, "clips", "S15_freeze.mp4")
if not os.path.exists(s15_freeze):
    # 先取原 S15 末帧图片
    last_frame = os.path.join(TMP, "s15_last.png")
    ff(["ffmpeg", "-y", "-sseof", "-0.1", "-i", s15_clip,
        "-frames:v", "1", last_frame])
    # 做成 1.5s 缓慢推近定格
    ff(["ffmpeg", "-y", "-loop", "1", "-i", last_frame,
        "-t", "1.5", "-vf",
        "fps=24,zoompan=z='min(zoom+0.0015,1.04)':d=36:s=720x1280,fade=t=out:st=1.0:d=0.5",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", s15_freeze])
    print("  S15 定格 1.5s + 推近 + 渐黑 完成")
clip_files["S15_freeze"] = s15_freeze

print("\n所有片段裁剪完成")
print(f"  共 {len(clip_files)} 个片段")
