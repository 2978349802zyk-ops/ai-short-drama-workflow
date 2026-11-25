"""
EP01 精剪 v5 — 视频拼接（带 xfade 叠化转场） + 完整音轨
"""
import subprocess, os

ROOT = r"D:\Hermes环境准备\AI漫剧制作\短剧项目\回声公寓"
OUT = os.path.join(ROOT, "07_剪辑工程")
TMP = os.path.join(OUT, "tmp_v5")
CLIPS = os.path.join(TMP, "clips")
AUD = os.path.join(ROOT, "05_配音与音效", "EP01_v2_Serena_去电音")

def ff(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("CMD:", " ".join(cmd[:8]), "...")
        print("ERR:", r.stderr[-3000:])
        raise RuntimeError("ffmpeg failed")
    return r

# ============================================================
# 视频拼接：用 xfade 滤镜做叠化转场
# ============================================================
# 转场列表：(上一段, 下一段, 转场类型, 转场时长, offset_from_start_of_prev)
# offset = 上一段时长 - 转场时长
# 蒙太奇内：硬切为主（只有 A4→A5 用 fade，A5→A6 用 fade to black）
# 正常叙事：每两个镜头之间 0.25s crossfade
# 奇观切换（S04→S05, S08→S09, S12→S13）：0.1s 闪帧 + 叠化柔化

# 先用 ffprobe 测每个片段实际时长
def get_dur(path):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                        "-show_entries", "format=duration", path],
                       capture_output=True, text=True)
    import json
    return float(json.loads(r.stdout)["format"]["duration"])

clip_order = [
    # 蒙太奇 6s
    ("A1", 0.3, "fade"),      # A1 本身有 fade in（在裁片段时做的？没有，在这补）
    ("A2", 0.0, "none"),      # 硬切
    ("A3", 0.0, "none"),      # 硬切
    ("A4", 0.2, "fade"),      # 0.2s 叠化进入
    ("A5", 0.2, "fade"),      # 0.2s fade to black
    ("A6", 0.0, "none"),      # 黑屏，1.5s
    # 正常叙事
    ("S02", 0.25, "fade"),    # 黑屏后淡入 S02
    ("S03", 0.25, "fade"),
    ("S04", 0.25, "fade"),
    ("S05", 0.1, "fade"),     # 第一奇观，短叠化 + 微闪
    ("S07", 0.25, "fade"),
    ("S08", 0.25, "fade"),
    ("S09", 0.1, "fade"),     # 第二奇观
    ("S10", 0.25, "fade"),
    ("S11", 0.2, "fade"),     # 情绪升级，稍短
    ("S12", 0.1, "fade"),     # 门开，短叠化
    ("S13", 0.1, "fade"),     # 第三奇观
    ("S14", 0.2, "fade"),     # 逃跑，快节奏
    ("S15", 0.2, "fade"),
    ("S15_freeze", 0.15, "fade"),  # 定格，短叠化
]

# 测时长
durs = {}
for cid, _, _ in clip_order:
    p = os.path.join(CLIPS, f"{cid}_clip.mp4" if cid != "A6" else "A6_clip.mp4")
    # A4 是 fast 版本
    if cid == "A4":
        p = os.path.join(CLIPS, "A4_clip_fast.mp4")
    if cid == "S15_freeze":
        p = os.path.join(CLIPS, "S15_freeze.mp4")
    durs[cid] = get_dur(p)
    print(f"  {cid}: {durs[cid]:.3f}s")

# 计算 xfade offset 链
# 第一个片段开始累计时间 T，每次 xfade 后 T += prev_dur - xfade_dur
# 第 i 个 xfade 的 offset = T - xfade_dur（从第 i 段开头算）
# 用 xfade 滤镜链：[0][1]xfade=...[x1]; [x1][2]xfade=...[x2]; ...

inputs = []
for cid, _, _ in clip_order:
    if cid == "A6":
        inputs.append(os.path.join(CLIPS, "A6_clip.mp4"))
    elif cid == "A4":
        inputs.append(os.path.join(CLIPS, "A4_clip_fast.mp4"))
    elif cid == "S15_freeze":
        inputs.append(os.path.join(CLIPS, "S15_freeze.mp4"))
    else:
        inputs.append(os.path.join(CLIPS, f"{cid}_clip.mp4"))

# 构建 xfade filter_complex
# 方法：用 concat 不行（要叠化），用 xfade 链
n = len(clip_order)
filter_parts = []
current_label = "0:v"
cumulative = durs[clip_order[0][0]]  # 第一段时长

for i in range(1, n):
    cid_prev, xfade_dur, xfade_type = clip_order[i-1]
    cid_curr, _, _ = clip_order[i]
    _, xfade_dur2, xfade_type2 = clip_order[i-1] if i == 1 else clip_order[i-1]
    # 第 i 个转场的实际参数是 clip_order[i] 的转场类型？不对：
    # 重新理：clip_order[i] 的第二个参数是「进入第 i 段时的转场时长」
    # 即从第 i-1 段转到第 i 段，用 clip_order[i][1] 的时长和 clip_order[i][2] 的类型
    _, xd, xt = clip_order[i]
    
    if xd <= 0.001:
        # 硬切，直接 concat 或 offset=0 的 xfade
        xd = 0.001  # 不能为 0
    
    # offset = 第 i-1 段结束前 xd 秒 = cumulative - xd
    offset = cumulative - xd
    offset = max(0.001, offset)
    
    next_label = f"x{i}" if i < n-1 else "vout"
    # dissolve = 标准 crossfade 叠化
    filter_parts.append(
        f"[{current_label}][{i}:v]xfade=transition=dissolve:duration={xd}:offset={offset}[{next_label}]"
    )
    current_label = next_label
    cumulative = cumulative + durs[cid_curr] - xd

filter_complex = ";".join(filter_parts)
print(f"\n总时长: {cumulative:.2f}s")
print(f"转场数: {len(filter_parts)}")

video_only = os.path.join(TMP, "video_only.mp4")
cmd = ["ffmpeg", "-y"]
for inp in inputs:
    cmd += ["-i", inp]
cmd += ["-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "24",
        video_only]
print("\n拼接视频...")
ff(cmd)
print(f"  视频无音轨版: {video_only}")
vdur = get_dur(video_only)
print(f"  实际时长: {vdur:.3f}s")
