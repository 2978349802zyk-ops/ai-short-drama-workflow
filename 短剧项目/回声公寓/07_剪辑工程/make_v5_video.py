# -*- coding: utf-8 -*-
"""
EP01 精剪 v5 构建脚本 — 视频部分
核心变化 vs v4：
1. 开场 7 秒全新数字特写蒙太奇（6 个裁切特写 + 文字钩子卡）
2. 正片压缩：S05 7.0 / S09 8.0 / S10 7.0 / S02 4.6 / S15a 4.2
3. 特写片段带 zoompan 慢推 + 锐化补偿
输出：tmp_v5/EP01_v5_video.mp4（无音轨）
"""
import subprocess, os, json

BASE = "D:/Hermes环境准备/AI漫剧制作/短剧项目/回声公寓"
SRC = f"{BASE}/06_视频素材"
OUT = f"{BASE}/07_剪辑工程/tmp_v5/clips"
TMP = f"{BASE}/07_剪辑工程/tmp_v5"
FINAL_VIDEO = f"{TMP}/EP01_v5_video.mp4"
os.makedirs(OUT, exist_ok=True)

FF = "ffmpeg"
ENC_V = ["-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24", "-an"]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-3000:])
        raise RuntimeError("ffmpeg failed: " + " ".join(cmd[:8]))
    return r

def get_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1", path], capture_output=True, text=True)
    return float(r.stdout.strip())

GRADE_COOL = "eq=brightness=-0.05:contrast=1.08:saturation=0.85,colorbalance=bs=0.06"
GRADE_WARM = "eq=brightness=-0.03:contrast=1.08:saturation=0.90,colorbalance=rs=0.04:gs=0.02"
GRADE_NEUTRAL = "eq=brightness=-0.04:contrast=1.08:saturation=0.87"
SAFE_CROP = "crop=iw*0.98:ih*0.98:(iw*0.02)/2:(ih*0.02)/2,scale=720:1280"

SLOW_PUSH = ("zoompan=z='min(1.0+on/24*0.06,1.06)':d=1:"
             "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=24")
SHARPEN = "unsharp=5:5:0.9:5:5:0.0"

# ============================================================
# Part 1: 开场数字特写蒙太奇（0-7s）
# ============================================================
print("=== Part 1: 数字特写蒙太奇 ===")

CU = [
    ("A1_fear",    "S15", 8.0, 180,  10, 360, 640, GRADE_COOL, 1.0, True),   # 惊恐脸
    ("A2_sign",    "S13", 2.5, 265, 410, 180, 320, GRADE_WARM, 0.8, True),   # 302门牌
    ("A3_hand",    "S11", 2.5, 370, 150, 300, 533, GRADE_COOL, 0.8, False),  # 拍门喊叫（含手）
    ("A4_linface", "S13", 2.5, 110, 199, 170, 302, GRADE_COOL, 0.7, False),  # 林晚侧脸
    ("A5_yingface","S13", 2.5, 475, 204, 170, 302, GRADE_WARM, 0.7, False),  # 影侧脸
    ("A6_slit",    "S06", 6.0, 440, 200, 200, 356, GRADE_WARM, 1.0, True),   # 门缝亮光特写
]
for name, tag, t, x, y, w, h, grade, dur, push in CU:
    vf = [f"crop={w}:{h}:{x}:{y}", "scale=720:1280:flags=lanczos", SHARPEN]
    if push: vf.append(SLOW_PUSH)
    vf.append(grade)
    if name == "A1_fear":
        vf.append("fade=t=in:st=0:d=0.15")
    if name == "A6_slit":
        vf.append("fade=t=out:st=%.3f:d=0.3" % (dur - 0.3))
    cmd = [FF,"-y","-ss",str(t),"-t",str(dur+0.2),"-i",f"{SRC}/EP01_{tag}.mp4",
           "-vf", ",".join(vf)] + ENC_V + [f"{OUT}/{name}.mp4"]
    run(cmd)
    print(" ", name, "OK")

# A7: 黑屏 + 文字钩子卡 2.0s
FONT = "simhei.ttf"
draw = (
    "drawtext=fontfile=%s:text='302':fontsize=170:fontcolor=white:"
    "x=(w-text_w)/2:y=400:alpha='if(lt(t,0.3),0,if(lt(t,0.8),(t-0.3)/0.5,1))',"
    "drawtext=fontfile=%s:text='三年没人住过·今晚亮着灯':fontsize=48:fontcolor=0xE8D9B0:"
    "x=(w-text_w)/2:y=640:alpha='if(lt(t,0.6),0,if(lt(t,1.1),(t-0.6)/0.5,1))'"
) % (FONT, FONT)
cmd = [FF,"-y","-f","lavfi","-i","color=c=black:s=720x1280:r=24:d=2.0",
       "-vf", draw] + ENC_V + [f"{OUT}/A7_hook.mp4"]
run(cmd)
print("  A7_hook OK")

# ============================================================
# Part 2: 正片片段
# ============================================================
print("=== Part 2: 正片 ===")

def graded_clip(src_file, start, dur, dst, grade, vf_extra=None, fade_in=0, fade_out=0, fade_color="black"):
    filters = [SAFE_CROP, grade]
    if vf_extra: filters.append(vf_extra)
    if fade_in > 0: filters.append(f"fade=t=in:st=0:d={fade_in}:color={fade_color}")
    if fade_out > 0: filters.append(f"fade=t=out:st={dur-fade_out:.3f}:d={fade_out}:color={fade_color}")
    run([FF,"-y","-ss",str(start),"-t",str(dur),"-i",src_file,"-vf",",".join(filters)] + ENC_V + [dst])

graded_clip(f"{SRC}/EP01_S02.mp4", 4.8, 4.6, f"{OUT}/01_S02.mp4", GRADE_COOL)
graded_clip(f"{SRC}/EP01_S03.mp4", 5.0, 2.2, f"{OUT}/02_S03.mp4", GRADE_NEUTRAL)
graded_clip(f"{SRC}/EP01_S04.mp4", 3.0, 3.7, f"{OUT}/03_S04.mp4", GRADE_COOL,
            fade_out=0.083, fade_color="white")
graded_clip(f"{SRC}/EP01_S05.mp4", 1.5, 7.0, f"{OUT}/04_S05.mp4", GRADE_WARM)
vf_s06 = f"{SAFE_CROP},{GRADE_WARM},{SLOW_PUSH}"
run([FF,"-y","-ss","0.0","-t","2.8","-i",f"{SRC}/EP01_S06.mp4","-vf",vf_s06] + ENC_V + [f"{OUT}/05_S06.mp4"])
run([FF,"-y","-i",f"{SRC}/EP01_S07.mp4","-filter_complex",
     "[0:v]trim=0:6,setpts=PTS-STARTPTS," + SAFE_CROP + "," + GRADE_COOL + "[v0];"
     "[0:v]trim=6:7,setpts=PTS-STARTPTS,setpts=PTS/0.9," + SAFE_CROP + "," + GRADE_COOL + "[v1];"
     "[0:v]trim=7:8.2,setpts=PTS-STARTPTS," + SAFE_CROP + "," + GRADE_COOL + "[v2];"
     "[v0][v1][v2]concat=n=3:v=1:a=0[outv]","-map","[outv]"] + ENC_V + [f"{OUT}/06_S07.mp4"])
vf_s08 = f"{SAFE_CROP},{GRADE_COOL},{SLOW_PUSH},fade=t=out:st=4.958:d=0.083:color=black"
run([FF,"-y","-ss","0.0","-t","5.04","-i",f"{SRC}/EP01_S08.mp4","-vf",vf_s08] + ENC_V + [f"{OUT}/07_S08.mp4"])
run([FF,"-y","-i",f"{SRC}/EP01_S09.mp4","-filter_complex",
     "[0:v]trim=0:7,setpts=PTS-STARTPTS," + SAFE_CROP + "," + GRADE_WARM + "[v0];"
     "[0:v]trim=7:8,setpts=PTS-STARTPTS,setpts=PTS/0.85," + SAFE_CROP + "," + GRADE_WARM + "[v1];"
     "[v0][v1]concat=n=2:v=1:a=0[outv]","-map","[outv]"] + ENC_V + [f"{OUT}/08_S09.mp4"])
graded_clip(f"{SRC}/EP01_S10.mp4", 0.0, 7.0, f"{OUT}/09_S10.mp4", GRADE_COOL,
            vf_extra="delogo=x=296:y=1012:w=136:h=96")
run([FF,"-y","-i",f"{SRC}/EP01_S11.mp4","-filter_complex",
     "[0:v]trim=0:1.42,setpts=PTS-STARTPTS," + SAFE_CROP + "," + GRADE_COOL + "[v0];"
     "[0:v]trim=1.42:1.92,setpts=PTS-STARTPTS,setpts=PTS/0.8," + SAFE_CROP + "," + GRADE_COOL + "[v1];"
     "[v0][v1]concat=n=2:v=1:a=0[outv]","-map","[outv]"] + ENC_V + [f"{OUT}/10_S11a.mp4"])
graded_clip(f"{SRC}/EP01_S11.mp4", 3.29, 1.75, f"{OUT}/10_S11b.mp4", GRADE_COOL)
graded_clip(f"{SRC}/EP01_S12.mp4", 5.0, 4.0, f"{OUT}/11_S12.mp4", GRADE_WARM,
            fade_out=0.083, fade_color="black")
graded_clip(f"{SRC}/EP01_S13.mp4", 0.0, 4.0, f"{OUT}/12_S13.mp4", GRADE_WARM)
run([FF,"-y","-i",f"{SRC}/EP01_S14.mp4","-filter_complex",
     "[0:v]trim=0:1,setpts=PTS-STARTPTS,setpts=PTS/1.2," + SAFE_CROP + "," + GRADE_COOL + "[v0];"
     "[0:v]trim=1:1.5,setpts=PTS-STARTPTS," + SAFE_CROP + "," + GRADE_COOL + "[v1];"
     "[v0][v1]concat=n=2:v=1:a=0[outv]","-map","[outv]"] + ENC_V + [f"{OUT}/13_S14.mp4"])
graded_clip(f"{SRC}/EP01_S15.mp4", 0.0, 4.2, f"{OUT}/14_S15a.mp4", GRADE_COOL)
run([FF,"-y","-ss","4.8","-i",f"{SRC}/EP01_S15.mp4","-vframes","1","-f","image2", f"{OUT}/s15_frame.png"])
vf_freeze = (f"{SAFE_CROP},{GRADE_COOL},"
    "zoompan=z='1.0+on/48*0.04':d=48:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=24,"
    "fade=t=out:st=0.8:d=1.2")
run([FF,"-y","-loop","1","-i",f"{OUT}/s15_frame.png","-t","2.0","-vf",vf_freeze,
     "-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-r","24","-an", f"{OUT}/14_S15b.mp4"])
print("正片片段完成")

# ============================================================
# Part 3: xfade 拼接 + 时间轴导出（供音轨使用）
# ============================================================
print("=== Part 3: xfade 拼接 ===")
clips_info = [
    ("A1_fear.mp4",    0.0),
    ("A2_sign.mp4",    0.0),
    ("A3_hand.mp4",    0.0),
    ("A4_linface.mp4", 0.0),
    ("A5_yingface.mp4",0.0),
    ("A6_slit.mp4",    0.15),
    ("A7_hook.mp4",    0.0),
    ("01_S02.mp4",     0.0),
    ("02_S03.mp4",     0.25),
    ("03_S04.mp4",     0.20),
    ("04_S05.mp4",     0.10),
    ("05_S06.mp4",     0.25),
    ("06_S07.mp4",     0.30),
    ("07_S08.mp4",     0.25),
    ("08_S09.mp4",     0.10),
    ("09_S10.mp4",     0.25),
    ("10_S11a.mp4",    0.20),
    ("10_S11b.mp4",    0.0),
    ("11_S12.mp4",     0.20),
    ("12_S13.mp4",     0.10),
    ("13_S14.mp4",     0.25),
    ("14_S15a.mp4",    0.20),
    ("14_S15b.mp4",    0.15),
]

# 交叉时长规范：0 表示硬切，但 xfade 在 duration<1帧时会塌陷输出长度，统一抬到 1 帧（视觉等同硬切）
MIN_XF = 1.0/24
clips_info = [(n, x if x > 0.001 else MIN_XF) for n, x in clips_info]

durs, starts = [], [0.0]
for fname, _ in clips_info:
    durs.append(get_dur(f"{OUT}/{fname}"))
for i in range(1, len(clips_info)):
    off = starts[i-1] + durs[i-1] - clips_info[i][1]
    starts.append(off)
total = starts[-1] + durs[-1]
print("各片段起点/时长:")
for (fname, xf), s, d in zip(clips_info, starts, durs):
    print(f"  {fname:18s} start={s:7.3f} dur={d:6.3f}")
print(f"总时长: {total:.3f}s")

with open(f"{TMP}/timeline.json","w",encoding="utf-8") as f:
    json.dump({"clips":[{"name":n,"xfade":x,"start":round(s,3),"dur":round(d,3)} for (n,x),s,d in zip(clips_info,starts,durs)],
               "total": round(total,3)}, f, ensure_ascii=False, indent=1)

n = len(clips_info)
inputs = []
for fname, _ in clips_info:
    inputs += ["-i", f"{OUT}/{fname}"]
# 全部走 xfade；硬切位置已统一抬到 1 帧交叉（见上 MIN_XF）。concat 混链会破坏 timebase，别用。
fc, prev = [], "[0:v]"
L = durs[0]
for i in range(1, n):
    xf = clips_info[i][1]
    outl = f"[v{i}]" if i < n-1 else "[outv]"
    off = L - xf
    fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={xf:.4f}:offset={off:.3f}{outl}")
    L = L - xf + durs[i]
    prev = outl
cmd = [FF,"-y"] + inputs + ["-filter_complex", ";".join(fc), "-map","[outv]"] + ENC_V + [FINAL_VIDEO]
run(cmd)
print("拼接完成:", FINAL_VIDEO, f"{get_dur(FINAL_VIDEO):.3f}s")
