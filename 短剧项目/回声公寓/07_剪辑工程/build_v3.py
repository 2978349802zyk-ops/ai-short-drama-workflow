"""
EP01 粗剪 v3 剪辑脚本
开场蒙太奇 + 微变速 + 微闪帧 + 呼吸感推镜 + 正常叙事段
输出：EP01_粗剪_v3.mp4（720x1280, 24fps, libx264 CRF18, 无音轨）
"""
import subprocess
import os

BASE = "D:/Hermes环境准备/AI漫剧制作/短剧项目/回声公寓"
SRC = f"{BASE}/06_视频素材"
V2 = f"{BASE}/07_剪辑工程/tmp_v2/clips"
OUT = f"{BASE}/07_剪辑工程/tmp_v3/clips"
FINAL = f"{BASE}/07_剪辑工程/EP01_粗剪_v3.mp4"
CONCAT = f"{BASE}/07_剪辑工程/tmp_v3/concat_list.txt"

os.makedirs(OUT, exist_ok=True)

FF = "ffmpeg"
ENC = ["-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24", "-an"]

def run(cmd):
    print(" ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2000:])
        raise RuntimeError("ffmpeg failed")
    return r

def clip(src, start, dur, dst, vf=None):
    """Trim + optional vf filter, output as h264 yuv420p 24fps"""
    cmd = [FF, "-y", "-ss", str(start), "-t", str(dur), "-i", src]
    if vf:
        cmd += ["-vf", vf]
    cmd += ENC + [dst]
    run(cmd)

def clip_dissolve(src, start, dur, dst, fade_in=0, fade_out=0, vf_extra=None):
    """Clip with fade in/out"""
    filters = []
    if vf_extra:
        filters.append(vf_extra)
    if fade_in > 0:
        filters.append(f"fade=t=in:st=0:d={fade_in}")
    if fade_out > 0:
        filters.append(f"fade=t=out:st={dur - fade_out}:d={fade_out}")
    vf = ",".join(filters) if filters else None
    clip(src, start, dur, dst, vf=vf)

# ============================================================
# 第一部分：开场蒙太奇（0-6s）
# ============================================================
print("=== 开场蒙太奇 ===")

# A1: S05 眼睛近景 1.0s，fade in 0.3s
# S05 是门后倒影，取 2.0-3.0s 眼睛最清晰处
clip_dissolve(f"{SRC}/EP01_S05.mp4", 2.0, 1.0, f"{OUT}/A1_S05_eye.mp4",
              fade_in=0.3)

# A2: S02 惊讶表情特写 0.5s，硬切
# S02 第 5.5-6.0s（停步后抬头瞬间）
clip(f"{SRC}/EP01_S02.mp4", 5.5, 0.5, f"{OUT}/A2_S02_face.mp4")

# A3: S06 眼睛眨一下 0.5s，硬切
# S06 第 1.5-2.0s 眨眼瞬间
clip(f"{SRC}/EP01_S06.mp4", 1.5, 0.5, f"{OUT}/A3_S06_blink.mp4")

# A4: S03 门缝微光 1.5s，1.1x 微加速模拟推近，叠化转场 0.2s（这里用 fade in 代替，叠化靠 concat 阶段做不了，用 xfade 更复杂）
# 1.5s 输出 = 1.5/1.1 = 1.36s 原素材
# 取 2.0-3.36s，setpts=PTS/1.1 加速
src_dur_a4 = 1.5 / 1.1
clip(f"{SRC}/EP01_S03.mp4", 2.0, src_dur_a4, f"{OUT}/A4_S03_door.mp4",
     vf="setpts=PTS/1.1,fade=t=in:st=0:d=0.2")

# A5: S04 暗部 1.0s，fade to black
# S04 末尾暗部，取 7.0-8.0s
clip_dissolve(f"{SRC}/EP01_S04.mp4", 7.0, 1.0, f"{OUT}/A5_S04_dark.mp4",
              fade_out=0.5)

# A6: 黑屏 1.5s
# 用 color 滤镜生成纯黑帧
cmd = [FF, "-y", "-f", "lavfi", "-i", "color=c=black:s=720x1280:r=24:d=1.5",
       "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-an",
       f"{OUT}/A6_black.mp4"]
run(cmd)

print("蒙太奇片段完成")

# ============================================================
# 第二部分：正常叙事段（沿用 v2 删减口径 + 微变速 + 推镜 + 闪帧）
# ============================================================
print("=== 正常叙事段（v2 基础上优化）===")

# S02：停步片段 5s（从 5.0-10.0s），无特殊处理
# 注意：开场蒙太奇用的是 S02 第 5.5-6.0s 的表情特写，跟这里是同素材不同段
clip(f"{SRC}/EP01_S02.mp4", 5.0, 5.0, f"{OUT}/01_S02.mp4")

# S03：2.5s（5.0-7.5s），中段压缩 0.5s
clip(f"{SRC}/EP01_S03.mp4", 5.0, 2.5, f"{OUT}/02_S03.mp4")

# S04：4s（3.0-7.0s），尾端加 2 帧白闪
# 白闪用 fade=white 最后几帧
clip(f"{SRC}/EP01_S04.mp4", 3.0, 4.0, f"{OUT}/03_S04.mp4",
     vf="fade=t=out:st=3.917:d=0.083:color=white")  # 最后2帧白闪（0.083s）

# S05：全用 10.04s（门后倒影，第一个大奇观）
# v2 全用，这里保持
clip(f"{SRC}/EP01_S05.mp4", 0.0, 10.04, f"{OUT}/04_S05.mp4")

# S06：3.5s（0-3.5s），尾 2s 做 digital zoom-in 1.0→1.05
# 压缩 1s，前半段信息密度最高
# 3.5s = 84帧，前 1.5s=36帧，后 2s=48帧
vf_s06 = (
    "zoompan=z='if(lte(on,36),1.0,1.0+(on-36)/48*0.05)':"
    "d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=24"
)
clip(f"{SRC}/EP01_S06.mp4", 0.0, 3.5, f"{OUT}/05_S06.mp4", vf=vf_s06)

# S07：8.54s（0-8.54s），砍尾部 1.5s 静态；水落地瞬间 0.9x 慢放
# 水落地在第 6-7s，做这一段 0.9x 慢放
# 分段：0-6s 正常 + 6-7s 0.9x + 7-8.54s 正常
cmd = [FF, "-y",
       "-i", f"{SRC}/EP01_S07.mp4",
       "-filter_complex",
       "[0:v]trim=0:6,setpts=PTS-STARTPTS[v0];"
       "[0:v]trim=6:7,setpts=PTS-STARTPTS,setpts=PTS/0.9[v1];"
       "[0:v]trim=7:8.54,setpts=PTS-STARTPTS[v2];"
       "[v0][v1][v2]concat=n=3:v=1:a=0[outv]",
       "-map", "[outv]"] + ENC + [f"{OUT}/06_S07.mp4"]
run(cmd)

# S08：全用 5.04s，尾 2s zoom 1.0→1.03
# 5.04s = 121帧，前3.04s=73帧，后2s=48帧
vf_s08 = (
    "zoompan=z='if(lte(on,73),1.0,1.0+(on-73)/48*0.03)':"
    "d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=24"
)
clip(f"{SRC}/EP01_S08.mp4", 0.0, 5.04, f"{OUT}/07_S08.mp4", vf=vf_s08)

# S09：全用 10.04s，最后 1s 放慢到 0.85x（对掌瞬间慢放）
# 前 9.04s 正常 + 最后 1s 0.85x
cmd = [FF, "-y",
       "-i", f"{SRC}/EP01_S09.mp4",
       "-filter_complex",
       "[0:v]trim=0:9.04,setpts=PTS-STARTPTS[v0];"
       "[0:v]trim=9.04:10.04,setpts=PTS-STARTPTS,setpts=PTS/0.85[v1];"
       "[v0][v1]concat=n=2:v=1:a=0[outv]",
       "-map", "[outv]"] + ENC + [f"{OUT}/08_S09.mp4"]
run(cmd)

# S10：8.5s（0-8.5s） + delogo，砍尾 1.5s 控时长
clip(f"{SRC}/EP01_S10.mp4", 0.0, 8.5, f"{OUT}/09_S10.mp4",
     vf="delogo=x=296:y=1012:w=136:h=96")

# S11a：前段 0-1.92s（推门起势），最后一下拍门 0.8x 慢放
# 拍门在最后 0.5s，做 0.8x
# 前 1.42s 正常 + 后 0.5s 0.8x
cmd = [FF, "-y",
       "-i", f"{SRC}/EP01_S11.mp4",
       "-filter_complex",
       "[0:v]trim=0:1.42,setpts=PTS-STARTPTS[v0];"
       "[0:v]trim=1.42:1.92,setpts=PTS-STARTPTS,setpts=PTS/0.8[v1];"
       "[v0][v1]concat=n=2:v=1:a=0[outv]",
       "-map", "[outv]"] + ENC + [f"{OUT}/10_S11a.mp4"]
run(cmd)

# S11b：后段 3.29-5.04s（硬接前段）
clip(f"{SRC}/EP01_S11.mp4", 3.29, 1.75, f"{OUT}/10_S11b.mp4")

# S12：4s（5.0-9.0s），有效开门段
clip(f"{SRC}/EP01_S12.mp4", 5.0, 4.0, f"{OUT}/11_S12.mp4")

# S13：3.5s（0-3.5s），双人同框对峙，砍尾 0.5s
clip(f"{SRC}/EP01_S13.mp4", 0.0, 3.5, f"{OUT}/12_S13.mp4")

# S14：1.5s（0-1.5s），前 1s 加速到 1.2x 增强爆发力
# 0-1s: 1.2x 加速 → 输出时长 1/1.2 = 0.833s
# 1-1.5s: 正常 → 0.5s
# 总输出约 1.333s
cmd = [FF, "-y",
       "-i", f"{SRC}/EP01_S14.mp4",
       "-filter_complex",
       "[0:v]trim=0:1,setpts=PTS-STARTPTS,setpts=PTS/1.2[v0];"
       "[0:v]trim=1:1.5,setpts=PTS-STARTPTS[v1];"
       "[v0][v1]concat=n=2:v=1:a=0[outv]",
       "-map", "[outv]"] + ENC + [f"{OUT}/13_S14.mp4"]
run(cmd)

# S15a：4s 动态（0-4s）
clip(f"{SRC}/EP01_S15.mp4", 0.0, 4.0, f"{OUT}/14_S15_part1.mp4")

# S15b：定格 1s + zoom 推近 1.0→1.04（推近到脸上僵住）
# 先抽第 4 秒帧，生成 1s 定格 + zoom
vf_freeze = (
    "zoompan=z='1.0+on/24*0.04':"
    "d=24:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=24"
)
# 从第 4 秒取 1 帧，做 24 帧 zoompan
cmd = [FF, "-y", "-ss", "4.0", "-i", f"{SRC}/EP01_S15.mp4",
       "-vframes", "1", "-f", "image2", f"{OUT}/s15_freeze.png"]
run(cmd)
cmd = [FF, "-y", "-loop", "1", "-i", f"{OUT}/s15_freeze.png",
       "-t", "1", "-vf", vf_freeze,
       "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24", "-an",
       f"{OUT}/14_S15_freeze.mp4"]
run(cmd)

# ============================================================
# 微闪帧（奇观切镜处加 2 帧闪）
# ============================================================
print("=== 微闪帧处理 ===")
# 闪帧在 S04→S05（白闪，已在 S04 尾部加），S08→S09（黑闪），S12→S13（黑闪）
# S08 尾部加 2 帧黑闪
clip(f"{OUT}/07_S08.mp4", 0.0, 5.04, f"{OUT}/07_S08_flash.mp4",
     vf="fade=t=out:st=4.958:d=0.083:color=black")

# S12 尾部加 2 帧黑闪
clip(f"{OUT}/11_S12.mp4", 0.0, 4.0, f"{OUT}/11_S12_flash.mp4",
     vf="fade=t=out:st=3.917:d=0.083:color=black")

# ============================================================
# 拼接
# ============================================================
print("=== 最终拼接 ===")

clip_order = [
    # 开场蒙太奇
    f"{OUT}/A1_S05_eye.mp4",
    f"{OUT}/A2_S02_face.mp4",
    f"{OUT}/A3_S06_blink.mp4",
    f"{OUT}/A4_S03_door.mp4",
    f"{OUT}/A5_S04_dark.mp4",
    f"{OUT}/A6_black.mp4",
    # 正常叙事段
    f"{OUT}/01_S02.mp4",
    f"{OUT}/02_S03.mp4",
    f"{OUT}/03_S04.mp4",      # 尾白闪 → S05
    f"{OUT}/04_S05.mp4",
    f"{OUT}/05_S06.mp4",
    f"{OUT}/06_S07.mp4",
    f"{OUT}/07_S08_flash.mp4", # 尾黑闪 → S09
    f"{OUT}/08_S09.mp4",
    f"{OUT}/09_S10.mp4",
    f"{OUT}/10_S11a.mp4",
    f"{OUT}/10_S11b.mp4",
    f"{OUT}/11_S12_flash.mp4", # 尾黑闪 → S13
    f"{OUT}/12_S13.mp4",
    f"{OUT}/13_S14.mp4",
    f"{OUT}/14_S15_part1.mp4",
    f"{OUT}/14_S15_freeze.mp4",
]

with open(CONCAT, "w", encoding="utf-8") as f:
    for p in clip_order:
        f.write(f"file '{p}'\n")

# 用 concat demuxer 拼接（所有片段已统一编码参数）
cmd = [FF, "-y", "-f", "concat", "-safe", "0", "-i", CONCAT,
       "-c", "copy", "-an", FINAL]
run(cmd)

# 校验时长
r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of",
                     "default=noprint_wrappers=1:nokey=1", FINAL],
                    capture_output=True, text=True)
print(f"\n最终时长: {r.stdout.strip()} 秒")
print(f"输出文件: {FINAL}")
