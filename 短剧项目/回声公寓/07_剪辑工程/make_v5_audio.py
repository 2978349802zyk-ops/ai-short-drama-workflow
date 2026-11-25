# -*- coding: utf-8 -*-
"""
EP01 精剪 v5 — 音轨部分（核心修复 v4 的两层硬伤）
修复1：BGM 从 45Hz 次低频改为 165/220/330Hz 中频层（手机扬声器可闻）+ 55Hz 低频垫底
修复2：声音事件全覆盖，消灭 26 秒死寂；母带 loudnorm LRA 压到 9
配音 7 条按 v5 新时间轴贴点（读 timeline.json）
输出：EP01_精剪_v5.mp4（带音轨）+ EP01_精剪_v5_音轨.wav
"""
import subprocess, os, json

BASE = "D:/Hermes环境准备/AI漫剧制作/短剧项目/回声公寓"
SFX_DIR = f"{BASE}/07_剪辑工程/tmp_v5/sfx"
AUD = f"{BASE}/05_配音与音效/EP01_v2_Serena_去电音"
TMP = f"{BASE}/07_剪辑工程/tmp_v5"
VIDEO = f"{TMP}/EP01_v5_video.mp4"
FINAL = f"{BASE}/07_剪辑工程/EP01_精剪_v5.mp4"
FINAL_WAV = f"{BASE}/07_剪辑工程/EP01_精剪_v5_音轨.wav"
os.makedirs(SFX_DIR, exist_ok=True)

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ERR:", r.stderr[-2000:])
        raise RuntimeError("ffmpeg failed")
    return r

def get_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1", path], capture_output=True, text=True)
    return float(r.stdout.strip())

tl = json.load(open(f"{TMP}/timeline.json", encoding="utf-8"))
TOTAL = tl["total"]
starts = {c["name"]: c["start"] for c in tl["clips"]}
print("总时长", TOTAL)

# ============================================================
# 1. 合成音效（全部本地 ffmpeg，不花钱）
# ============================================================
print("=== 合成音效 ===")
SR = 44100

def synth(name, src, dur):
    """src 是完整 lavfi 图（sine/anoisesrc 是源，必须走 -i 而不是 -af）"""
    p = f"{SFX_DIR}/{name}.wav"
    run(["ffmpeg","-y","-f","lavfi","-i",src,"-t",str(dur),
         "-af","aformat=sample_fmts=s16:channel_layouts=mono","-c:a","pcm_s16le", p])
    return p

# thump：低频重击（中频段 120Hz 短包络，手机可闻）
THUMP = ("sine=frequency=120:duration=0.5,volume=1.0,"
         "afade=t=in:st=0:d=0.005,afade=t=out:st=0.02:d=0.4,volume=0.9")
# scrape：金属刮擦（2-4kHz 带通噪声）
SCRAPE = ("anoisesrc=color=pink:duration=0.6,bandpass=f=2500:w=1500,"
          "tremolo=f=18:d=0.8,afade=t=out:st=0.1:d=0.45,volume=0.7")
# knock：拍门闷响
KNOCK = ("sine=frequency=95:duration=0.35,volume=1.0,"
         "afade=t=in:st=0:d=0.003,afade=t=out:st=0.015:d=0.3,volume=1.0,lowpass=f=400")
# heart：心跳双脉冲
HEART = ("sine=frequency=70:duration=0.8,volume=0.9,"
         "volume='if(lt(t,0.1),1,if(lt(t,0.18),0.15,if(lt(t,0.28),0.8,0)))':eval=frame,"
         "afade=t=out:st=0.3:d=0.4,lowpass=f=200")
# breath：呼吸（粉噪 400-900Hz，1.6s 包络）
BREATH = ("anoisesrc=color=pink:duration=1.6,bandpass=f=650:w=500,"
          "volume='0.9*abs(sin(PI*t/1.6))':eval=frame,volume=0.5")
# water：水洒（高通噪声突发+衰减）
WATER = ("anoisesrc=color=brown:duration=1.0,highpass=f=900,"
         "afade=t=in:st=0:d=0.01,afade=t=out:st=0.05:d=0.9,volume=0.8")
# phone：手机解锁短音
PHONE = ("sine=frequency=1200:duration=0.15,volume=0.5,afade=t=out:st=0.05:d=0.1")
# vibrate：震动
VIBRATE = ("sine=frequency=180:duration=0.5,tremolo=f=30:d=1,volume=0.35,lowpass=f=500")
# whoosh：呼啸
WHOOSH = ("anoisesrc=color=pink:duration=1.2,bandpass=f=700:w=600,"
          "volume='0.8*sin(PI*t/1.2)':eval=frame,volume=0.7")
# tinnitus：耳鸣（极轻高频）
TINN = ("sine=frequency=3600:duration=3.0,volume=0.12,afade=t=in:st=0:d=0.8,afade=t=out:st=2.0:d=1.0")
# creak：门轴吱呀（滑频）
CREAK = ("sine=frequency=350:duration=1.8,vibrato=f=6:d=0.6,"
         "volume='0.5*(0.6+0.4*sin(2*PI*0.7*t))':eval=frame,afade=t=out:st=1.2:d=0.5,volume=0.45")
# step：脚步
STEP = ("sine=frequency=110:duration=0.22,volume=0.8,"
        "afade=t=in:st=0:d=0.004,afade=t=out:st=0.02:d=0.18,lowpass=f=300")
# click：门锁咔哒
CLICK = ("anoisesrc=color=white:duration=0.08,highpass=f=1500,volume=0.55,"
         "afade=t=out:st=0.01:d=0.06")
# riser：张力上升（正片进入前）
RISER = ("sine=frequency=180:duration=1.8,vibrato=f=5:d=0.3,"
         "volume='0.5*t/1.8':eval=frame,afade=t=out:st=1.5:d=0.3,volume=0.5")

sfx = {}
for nm, f, d in [("thump",THUMP,0.5),("scrape",SCRAPE,0.6),("knock",KNOCK,0.35),
                 ("heart",HEART,0.8),("breath",BREATH,1.6),("water",WATER,1.0),
                 ("phone",PHONE,0.15),("vibrate",VIBRATE,0.5),("whoosh",WHOOSH,1.2),
                 ("tinn",TINN,3.0),("creak",CREAK,1.8),("step",STEP,0.22),
                 ("click",CLICK,0.08),("riser",RISER,1.8)]:
    sfx[nm] = synth(nm, f, d)
print("音效合成完成:", len(sfx))

# ============================================================
# 2. 事件表（按 v5 时间轴；每 1.5-2s 一个事件，无死寂）
# ============================================================
s02 = starts["01_S02.mp4"]; s03 = starts["02_S03.mp4"]; s04 = starts["03_S04.mp4"]
s05 = starts["04_S05.mp4"]; s06 = starts["05_S06.mp4"]; s07 = starts["06_S07.mp4"]
s08 = starts["07_S08.mp4"]; s09 = starts["08_S09.mp4"]; s10 = starts["09_S10.mp4"]
s11a = starts["10_S11a.mp4"]; s11b = starts["10_S11b.mp4"]; s12 = starts["11_S12.mp4"]
s13 = starts["12_S13.mp4"]; s14 = starts["13_S14.mp4"]; s15a = starts["14_S15a.mp4"]
s15b = starts["14_S15b.mp4"]

events = []  # (音效名, 贴点秒, 音量, 重复间隔可选)
# 开场 0-7s
events += [
    ("whoosh", 0.0, 0.8), ("thump", 0.85, 1.0), ("scrape", 1.65, 0.7),
    ("knock", 2.45, 1.0), ("heart", 3.35, 0.9), ("heart", 4.55, 0.9),
    ("click", 5.5, 0.8), ("riser", 5.3, 0.7),
]
# S02 停步：脚步×3 + 环境
for i in range(3): events.append(("step", s02 + 0.6 + i*0.75, 0.75))
events += [("breath", s02 + 2.8, 0.6)]
# S03 凑近门缝
events += [("breath", s03 + 0.3, 0.7), ("step", s03 + 0.1, 0.6)]
# S04 摇镜：吸气 + 白闪前 whoosh
events += [("breath", s04 + 1.2, 0.7), ("whoosh", s04 + 3.0, 0.8), ("thump", s04 + 3.62, 1.0)]
# S05 门后倒影（奇观1）：耳鸣 + 心跳
events += [("tinn", s05 + 0.3, 0.5), ("heart", s05 + 2.0, 0.85), ("heart", s05 + 4.0, 0.85)]
# S06 对视
events += [("breath", s06 + 0.4, 0.7), ("heart", s06 + 1.5, 0.9)]
# S07 后退洒水：水声 + 急呼吸 + 心跳
events += [("water", s07 + 5.95, 1.0), ("breath", s07 + 6.3, 0.8), ("heart", s07 + 7.2, 0.9)]
# S08 手机：解锁 + 震动
events += [("phone", s08 + 1.0, 0.8), ("vibrate", s08 + 1.3, 0.7), ("breath", s08 + 3.0, 0.6)]
# S09 镜像同步（奇观2）：心跳放大 + 耳鸣
events += [("heart", s09 + 1.0, 1.0), ("heart", s09 + 3.0, 1.0), ("tinn", s09 + 4.5, 0.4)]
# S10 回声问答
events += [("heart", s10 + 3.0, 0.8), ("breath", s10 + 5.0, 0.6)]
# S11 崩溃拍门：连击 ×5
for i in range(5): events.append(("knock", s11a + 0.15 + i*0.38, 1.0))
for i in range(3): events.append(("knock", s11b + 0.2 + i*0.5, 0.9))
# S12 门开：吱呀
events += [("creak", s12 + 0.3, 0.9), ("breath", s12 + 2.2, 0.7)]
# S13 双人同框（奇观3）：重低音 + 耳鸣
events += [("thump", s13 + 0.3, 1.0), ("tinn", s13 + 0.8, 0.5), ("heart", s13 + 2.0, 0.9)]
# S14 转身跑：脚步×3
for i in range(3): events.append(("step", s14 + 0.15 + i*0.3, 0.9))
# S15 结尾：心跳渐缓
events += [("heart", s15a + 1.0, 0.8), ("heart", s15a + 2.6, 0.7), ("heart", s15b + 0.5, 0.6)]
# 结尾黑屏前 riser
events += [("riser", max(0, s15b - 0.2), 0.5)]

print("事件数:", len(events))

# ============================================================
# 3. 配音贴点（新时间轴）
# ============================================================
voices = [
    (f"{AUD}/S02_林晚_几点了.wav",   s02 + 0.8, 1.0),
    (f"{AUD}/S03_林晚_302的光.wav",  s03 + 0.5, 1.0),
    (f"{AUD}/S04_林晚_谁.wav",       s04 + 1.5, 1.0),
    (f"{AUD}/S05_影_谁.wav",         s05 + 2.5, 0.85),
    (f"{AUD}/S10_林晚_你是谁.wav",   s10 + 0.5, 1.0),
    (f"{AUD}/S10_影_你是谁_延迟2s.wav", s10 + 0.5, 0.85),
    (f"{AUD}/S11_林晚_崩溃.wav",     s11a + 0.2, 1.0),
]

# ============================================================
# 4. BGM 三层（中频可闻 + 低频垫底 + 粉噪纹理），全片连续
# ============================================================
print("=== 生成 BGM ===")
bgm_mid = f"{SFX_DIR}/bgm_mid.wav"
D = TOTAL + 2
run(["ffmpeg","-y",
     "-f","lavfi","-i",f"sine=frequency=165:duration={D:.1f}:sample_rate={SR}",
     "-f","lavfi","-i",f"sine=frequency=220:duration={D:.1f}:sample_rate={SR}",
     "-f","lavfi","-i",f"sine=frequency=330:duration={D:.1f}:sample_rate={SR}",
     "-f","lavfi","-i",f"anoisesrc=color=pink:duration={D:.1f}:sample_rate={SR}",
     "-filter_complex",
     "[0:a]volume=0.35[s1];[1:a]volume=0.30[s2];[2:a]volume=0.22[s3];"
     "[3:a]bandpass=f=800:w=1200,volume=0.06[n];"
     "[s1][s2][s3][n]amix=inputs=4:normalize=0,tremolo=f=0.25:d=0.5,volume=0.9,"
     "aformat=sample_fmts=s16:channel_layouts=mono[o]",
     "-map","[o]","-c:a","pcm_s16le", bgm_mid])

bgm_low = f"{SFX_DIR}/bgm_low.wav"
run(["ffmpeg","-y",
     "-f","lavfi","-i",f"sine=frequency=55:duration={D:.1f}:sample_rate={SR}",
     "-f","lavfi","-i",f"sine=frequency=82:duration={D:.1f}:sample_rate={SR}",
     "-filter_complex",
     "[0:a]volume=0.5[s];[1:a]volume=0.25[s2];"
     "[s][s2]amix=inputs=2:normalize=0,volume=0.35,"
     "aformat=sample_fmts=s16:channel_layouts=mono[o]",
     "-map","[o]","-c:a","pcm_s16le", bgm_low])
print("BGM 完成")

# ============================================================
# 5. 总混音：BGM(2) + 音效(N) + 配音(7) → loudnorm
# ============================================================
print("=== 总混音 ===")
inputs = ["-i", bgm_mid, "-i", bgm_low]
fc_parts = []
labels = []
idx = 2

# BGM 层：低频开场前稍弱，正片起稍强（用 volume 表达式按时间）
fc_parts.append(
    "[0:a]volume=1.0[mid];"
    "[1:a]volume='if(lt(t,7),0.5,0.9)':eval=frame[low]"
)
labels += ["[mid]", "[low]"]

for name, t, vol in events:
    inputs += ["-i", sfx[name]]
    ms = int(t*1000)
    fc_parts.append(f"[{idx}:a]adelay={ms}|{ms},volume={vol}[e{idx}]")
    labels.append(f"[e{idx}]")
    idx += 1

for path, t, vol in voices:
    inputs += ["-i", path]
    ms = max(0, int(t*1000))
    fc_parts.append(f"[{idx}:a]adelay={ms}|{ms},volume={vol}[v{idx}]")
    labels.append(f"[v{idx}]")
    idx += 1

n_in = idx
fc_parts.append(
    "".join(labels) + f"amix=inputs={n_in}:normalize=0,"
    "alimiter=limit=0.9,loudnorm=I=-16:TP=-1.5:LRA=9,"
    f"aresample={SR},atrim=0:{TOTAL:.3f}"
)
fc = ";".join(fc_parts)
cmd = ["ffmpeg","-y"] + inputs + ["-filter_complex", fc,
       "-map","[out]"] if False else ["ffmpeg","-y"] + inputs + ["-filter_complex", fc + "[out]", "-map","[out]"]
cmd += ["-c:a","pcm_s16le", FINAL_WAV]
run(cmd)
print("总混音完成:", FINAL_WAV)

# ============================================================
# 6. 与视频合并
# ============================================================
run(["ffmpeg","-y","-i", VIDEO, "-i", FINAL_WAV,
     "-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-b:a","192k",
     "-shortest", FINAL])
print("成片:", FINAL, f"{get_dur(FINAL):.3f}s")
