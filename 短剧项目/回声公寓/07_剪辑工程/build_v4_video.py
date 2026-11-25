"""
EP01 精剪 v4 构建脚本 — 上半部分：视频剪辑
叠化转场 + 动作匹配 + 调色 + 稳定 + 结尾定格推近
输出：tmp_v4/clips/ 下各片段 + EP01_精剪_v4_video.mp4（无音轨，等下半部分混音）
"""
import subprocess
import os

BASE = "D:/Hermes环境准备/AI漫剧制作/短剧项目/回声公寓"
SRC = f"{BASE}/06_视频素材"
OUT = f"{BASE}/07_剪辑工程/tmp_v4/clips"
TMP = f"{BASE}/07_剪辑工程/tmp_v4"
FINAL_VIDEO = f"{BASE}/07_剪辑工程/tmp_v4/EP01_v4_video.mp4"

os.makedirs(OUT, exist_ok=True)

FF = "ffmpeg"
ENC_V = ["-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24", "-an"]


def run(cmd):
    print(" ".join(cmd[:6]) + " ..." if len(cmd) > 6 else " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-3000:])
        raise RuntimeError("ffmpeg failed")
    return r


def get_dur(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


# 调色预设
# 冷调（走廊）：亮度-5%，对比+8%，饱和-15%，偏冷蓝
GRADE_COOL = (
    "eq=brightness=-0.05:contrast=1.08:saturation=0.85,"
    "colorbalance=bs=0.06"
)
# 暖调（门内）：亮度-3%，对比+8%，饱和-10%，偏暖黄
GRADE_WARM = (
    "eq=brightness=-0.03:contrast=1.08:saturation=0.90,"
    "colorbalance=rs=0.04:gs=0.02"
)
# 中性（过渡/混合光）：基础调色
GRADE_NEUTRAL = (
    "eq=brightness=-0.04:contrast=1.08:saturation=0.87"
)

# 安全框裁切 + 微缩放（去除边缘变形）
SAFE_CROP = "crop=iw*0.98:ih*0.98:(iw*0.02)/2:(ih*0.02)/2,scale=720:1280"


def graded_clip(src_file, start, dur, dst, grade, vf_extra=None, fade_in=0, fade_out=0, fade_color="black"):
    """带调色+安全框+可选淡入淡出的片段"""
    filters = [SAFE_CROP, grade]
    if vf_extra:
        filters.append(vf_extra)
    if fade_in > 0:
        filters.append(f"fade=t=in:st=0:d={fade_in}:color={fade_color}")
    if fade_out > 0:
        filters.append(f"fade=t=out:st={dur - fade_out}:d={fade_out}:color={fade_color}")
    vf = ",".join(filters)
    cmd = [FF, "-y", "-ss", str(start), "-t", str(dur), "-i", src_file,
           "-vf", vf] + ENC_V + [dst]
    run(cmd)


# ============================================================
# 第一部分：开场蒙太奇（0-6s）— 保持硬切冲击，仅关键处加叠化
# ============================================================
print("=== Part 1: 开场蒙太奇 ===")

# A1: S05眼睛近景 1.0s，fade in 0.3s（暖调）
graded_clip(f"{SRC}/EP01_S05.mp4", 2.0, 1.0, f"{OUT}/A1_eye.mp4",
            GRADE_WARM, fade_in=0.3)

# A2: S02惊讶脸 0.5s，硬切（冷调）
graded_clip(f"{SRC}/EP01_S02.mp4", 5.5, 0.5, f"{OUT}/A2_face.mp4",
            GRADE_COOL)

# A3: S06眨眼 0.5s，硬切（暖调）
graded_clip(f"{SRC}/EP01_S06.mp4", 1.5, 0.5, f"{OUT}/A3_blink.mp4",
            GRADE_WARM)

# A4: S03门缝微光 1.5s，1.1x加速模拟推近，fade in 0.2s（暖调从门缝透出）
src_dur_a4 = 1.5 / 1.1
graded_clip(f"{SRC}/EP01_S03.mp4", 2.0, src_dur_a4, f"{OUT}/A4_door.mp4",
            GRADE_WARM,
            vf_extra="setpts=PTS/1.1",
            fade_in=0.2)

# A5: S04暗部 1.0s，fade to black（冷调偏暗）
graded_clip(f"{SRC}/EP01_S04.mp4", 7.0, 1.0, f"{OUT}/A5_dark.mp4",
            GRADE_COOL, fade_out=0.5)

# A6: 黑屏 1.5s
cmd = [FF, "-y", "-f", "lavfi", "-i", "color=c=black:s=720x1280:r=24:d=1.5",
       "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-an",
       f"{OUT}/A6_black.mp4"]
run(cmd)

print("蒙太奇片段完成")

# ============================================================
# 第二部分：正常叙事段 — 精剪版
# ============================================================
print("=== Part 2: 正常叙事段 ===")

# 01 S02: 停步 5.2s（建立镜头，留呼吸空间），冷调
graded_clip(f"{SRC}/EP01_S02.mp4", 4.8, 5.2, f"{OUT}/01_S02.mp4", GRADE_COOL)

# 02 S03: 凑近门缝 2.2s（压0.3s），混合光→暖调渐显
graded_clip(f"{SRC}/EP01_S03.mp4", 5.0, 2.2, f"{OUT}/02_S03.mp4", GRADE_NEUTRAL)

# 03 S04: 摇镜暗部 3.7s（压0.3s），尾端白闪→S05奇观
graded_clip(f"{SRC}/EP01_S04.mp4", 3.0, 3.7, f"{OUT}/03_S04.mp4",
            GRADE_COOL,
            fade_out=0.083, fade_color="white")

# 04 S05: 门后倒影 10.04s（奇观，全用），暖调
graded_clip(f"{SRC}/EP01_S05.mp4", 0.0, 10.04, f"{OUT}/04_S05.mp4", GRADE_WARM)

# 05 S06: 眼睛特写 3.8s（加0.3s强化压迫感），尾2s digital zoom-in 1.0→1.05，暖调
vf_s06 = (
    "zoompan=z='if(lte(on,43),1.0,1.0+(on-43)/48*0.05)':"
    "d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=24"
)
# 先做调色+裁切，再做zoompan（因为zoompan会改变帧尺寸流程）
# 简化：直接在zoompan前加调色滤镜链
vf_s06_full = f"{SAFE_CROP},{GRADE_WARM},{vf_s06}"
cmd = [FF, "-y", "-ss", "0.0", "-t", "3.8", "-i", f"{SRC}/EP01_S06.mp4",
       "-vf", vf_s06_full] + ENC_V + [f"{OUT}/05_S06.mp4"]
run(cmd)

# 06 S07: 后退洒水 8.2s（压0.34s），水落地6-7s 0.9x慢放，冷调
# 分段：0-6s正常 + 6-7s 0.9x + 7-8.2s正常
cmd = [FF, "-y",
       "-i", f"{SRC}/EP01_S07.mp4",
       "-filter_complex",
       f"[0:v]trim=0:6,setpts=PTS-STARTPTS,{SAFE_CROP},{GRADE_COOL}[v0];"
       f"[0:v]trim=6:7,setpts=PTS-STARTPTS,setpts=PTS/0.9,{SAFE_CROP},{GRADE_COOL}[v1];"
       f"[0:v]trim=7:8.2,setpts=PTS-STARTPTS,{SAFE_CROP},{GRADE_COOL}[v2];"
       "[v0][v1][v2]concat=n=3:v=1:a=0[outv]",
       "-map", "[outv]"] + ENC_V + [f"{OUT}/06_S07.mp4"]
run(cmd)

# 07 S08: 手机微光 5.04s（全用），尾2s zoom 1.0→1.03，尾端黑闪→S09
vf_s08 = (
    "zoompan=z='if(lte(on,73),1.0,1.0+(on-73)/48*0.03)':"
    "d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=24"
)
vf_s08_full = f"{SAFE_CROP},{GRADE_COOL},{vf_s08},fade=t=out:st=4.958:d=0.083:color=black"
cmd = [FF, "-y", "-ss", "0.0", "-t", "5.04", "-i", f"{SRC}/EP01_S08.mp4",
       "-vf", vf_s08_full] + ENC_V + [f"{OUT}/07_S08.mp4"]
run(cmd)

# 08 S09: 镜像同步 10.04s，最后1s 0.85x慢放（对掌瞬间），暖调
cmd = [FF, "-y",
       "-i", f"{SRC}/EP01_S09.mp4",
       "-filter_complex",
       f"[0:v]trim=0:9.04,setpts=PTS-STARTPTS,{SAFE_CROP},{GRADE_WARM}[v0];"
       f"[0:v]trim=9.04:10.04,setpts=PTS-STARTPTS,setpts=PTS/0.85,{SAFE_CROP},{GRADE_WARM}[v1];"
       "[v0][v1]concat=n=2:v=1:a=0[outv]",
       "-map", "[outv]"] + ENC_V + [f"{OUT}/08_S09.mp4"]
run(cmd)

# 09 S10: 回声问答 8.2s（压0.3s）+ delogo，冷调
graded_clip(f"{SRC}/EP01_S10.mp4", 0.0, 8.2, f"{OUT}/09_S10.mp4",
            GRADE_COOL,
            vf_extra="delogo=x=296:y=1012:w=136:h=96")

# 10 S11a: 推门起势 + 拍门，最后0.5s 0.8x慢放，冷调
# 前1.42s正常 + 后0.5s 0.8x → 总输出 1.42 + 0.625 = 2.045s
cmd = [FF, "-y",
       "-i", f"{SRC}/EP01_S11.mp4",
       "-filter_complex",
       f"[0:v]trim=0:1.42,setpts=PTS-STARTPTS,{SAFE_CROP},{GRADE_COOL}[v0];"
       f"[0:v]trim=1.42:1.92,setpts=PTS-STARTPTS,setpts=PTS/0.8,{SAFE_CROP},{GRADE_COOL}[v1];"
       "[v0][v1]concat=n=2:v=1:a=0[outv]",
       "-map", "[outv]"] + ENC_V + [f"{OUT}/10_S11a.mp4"]
run(cmd)

# 11 S11b: 后段硬接（避开中段塌陷），冷调
graded_clip(f"{SRC}/EP01_S11.mp4", 3.29, 1.75, f"{OUT}/10_S11b.mp4", GRADE_COOL)

# 12 S12: 门开 4.0s，尾端黑闪→S13，暖调（门内光）
graded_clip(f"{SRC}/EP01_S12.mp4", 5.0, 4.0, f"{OUT}/11_S12.mp4",
            GRADE_WARM,
            fade_out=0.083, fade_color="black")

# 13 S13: 双人同框 4.0s（加0.5s，奇观看够），暖调
graded_clip(f"{SRC}/EP01_S13.mp4", 0.0, 4.0, f"{OUT}/12_S13.mp4", GRADE_WARM)

# 14 S14: 转身跑 1.33s（前1s 1.2x加速），冷调
cmd = [FF, "-y",
       "-i", f"{SRC}/EP01_S14.mp4",
       "-filter_complex",
       f"[0:v]trim=0:1,setpts=PTS-STARTPTS,setpts=PTS/1.2,{SAFE_CROP},{GRADE_COOL}[v0];"
       f"[0:v]trim=1:1.5,setpts=PTS-STARTPTS,{SAFE_CROP},{GRADE_COOL}[v1];"
       "[v0][v1]concat=n=2:v=1:a=0[outv]",
       "-map", "[outv]"] + ENC_V + [f"{OUT}/13_S14.mp4"]
run(cmd)

# 15 S15a: 中景发现异常 4.8s（加0.8s，拉长悬念），冷调
graded_clip(f"{SRC}/EP01_S15.mp4", 0.0, 4.8, f"{OUT}/14_S15a.mp4", GRADE_COOL)

# 16 S15b: 定格2.0s（加0.5s，钩子更明确）+ zoom 1.0→1.04 + 最后1s渐黑，冷调
# 抽第4.8秒帧
cmd = [FF, "-y", "-ss", "4.8", "-i", f"{SRC}/EP01_S15.mp4",
       "-vframes", "1", "-f", "image2", f"{OUT}/s15_frame.png"]
run(cmd)
# 定格 + zoom + fade out（2s：前0.8s推近+后1.2s渐黑）
vf_freeze = (
    f"{SAFE_CROP},{GRADE_COOL},"
    "zoompan=z='1.0+on/48*0.04':"
    "d=48:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=24,"
    "fade=t=out:st=0.8:d=1.2"
)
cmd = [FF, "-y", "-loop", "1", "-i", f"{OUT}/s15_frame.png",
       "-t", "2.0", "-vf", vf_freeze,
       "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24", "-an",
       f"{OUT}/14_S15b.mp4"]
run(cmd)

print("所有单片段完成")

# ============================================================
# 第三部分：xfade 叠化拼接
# ============================================================
print("=== Part 3: xfade 叠化拼接 ===")

# 片段顺序和叠化时长
# (文件名, 叠化时长s) — 第一个元素没有入叠化
clips_info = [
    # 蒙太奇（保持硬切冲击，只有A4→A5加叠化）
    ("A1_eye.mp4", 0),       # fade in 已内置
    ("A2_face.mp4", 0),      # 硬切
    ("A3_blink.mp4", 0),     # 硬切
    ("A4_door.mp4", 0.15),   # 从A3眨眼→门缝，微叠化
    ("A5_dark.mp4", 0.3),    # A4→A5 叠化（fade out已内置在A5里了，这里用xfade）
    ("A6_black.mp4", 0.3),   # A5→A6 叠化到黑
    # 叙事段（大部分 0.2-0.3s crossfade）
    ("01_S02.mp4", 0.0),     # 黑屏→S02，0叠化（从黑直接出画面，配合J-cut音效）
    ("02_S03.mp4", 0.25),    # S02→S03
    ("03_S04.mp4", 0.20),    # S03→S04
    ("04_S05.mp4", 0.10),    # S04白闪→S05，短叠化（闪帧前后各0.1s）
    ("05_S06.mp4", 0.25),    # S05→S06
    ("06_S07.mp4", 0.30),    # S06眼睛→S07后退惊吓，情绪转换
    ("07_S08.mp4", 0.25),    # S07→S08 动作匹配
    ("08_S09.mp4", 0.10),    # S08黑闪→S09，短叠化
    ("09_S10.mp4", 0.25),    # S09→S10
    ("10_S11a.mp4", 0.20),   # S10→S11a
    ("10_S11b.mp4", 0.0),    # 同镜硬接，无叠化
    ("11_S12.mp4", 0.20),    # S11b→S12 拍门→门开（动作匹配）
    ("12_S13.mp4", 0.10),    # S12黑闪→S13，短叠化
    ("13_S14.mp4", 0.25),    # S13→S14
    ("14_S15a.mp4", 0.20),   # S14→S15a
    ("14_S15b.mp4", 0.15),   # S15a→定格
]

# 构建 xfade filter_complex
# 策略：先读取所有片段作为输入，然后链式 xfade
# 注意：每个 xfade 的 offset = 前一个累计时长 - 叠化时长

# 先获取每个片段的实际时长
clip_durs = []
for fname, _ in clips_info:
    d = get_dur(f"{OUT}/{fname}")
    clip_durs.append(d)
    print(f"  {fname}: {d:.3f}s")

# 构建 filter_complex
inputs = []
for fname, _ in clips_info:
    inputs += ["-i", f"{OUT}/{fname}"]

n = len(clips_info)
filter_parts = []

# 第一个 xfade: [0][1]xfade -> x0
# 第二个: [x0][2]xfade -> x1
# ...

# 累计时长（输出时间轴上的）
running_dur = clip_durs[0]

prev_label = "0:v"
for i in range(1, n):
    xfade_dur = clips_info[i][1]  # 叠化时长
    offset = running_dur - xfade_dur  # xfade 起始偏移（在上一段的时间轴上）
    out_label = f"x{i-1}" if i < n - 1 else "outv"

    filter_parts.append(
        f"[{prev_label}][{i}:v]xfade=transition=fade:duration={xfade_dur}:offset={offset}[{out_label}]"
    )

    # 更新累计时长
    running_dur = running_dur + clip_durs[i] - xfade_dur
    prev_label = out_label

filter_complex = ";".join(filter_parts)

print(f"预计总时长: {running_dur:.3f}s")

cmd = [FF, "-y"] + inputs + [
    "-filter_complex", filter_complex,
    "-map", "[outv]",
] + ENC_V + [FINAL_VIDEO]
run(cmd)

# 校验
actual_dur = get_dur(FINAL_VIDEO)
print(f"\n视频总时长: {actual_dur:.3f} 秒")
print(f"视频输出: {FINAL_VIDEO}")
