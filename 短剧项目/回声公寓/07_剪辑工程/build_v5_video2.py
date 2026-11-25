"""
EP01 精剪 v5 — concat + fade 拼接（不依赖 xfade offset 计算）
"""
import subprocess, os, json

ROOT = r"D:\Hermes环境准备\AI漫剧制作\短剧项目\回声公寓"
OUT = os.path.join(ROOT, "07_剪辑工程")
TMP = os.path.join(OUT, "tmp_v5")
NORM = os.path.join(TMP, "norm")
CLIPS = os.path.join(TMP, "clips")

def ff(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ERR:", r.stderr[-1500:])
        raise RuntimeError("ffmpeg failed")
    return r

def get_dur(path):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                        "-show_entries", "format=duration", path],
                       capture_output=True, text=True)
    return float(json.loads(r.stdout)["format"]["duration"])

clip_order = [
    ("A1", 0.3),      # 1s
    ("A2", 0),       # 硬切（0.5s）
    ("A3", 0),       # 硬切（0.5s）
    ("A4", 0),       # 1.4s（加速版），硬切
    ("A5", 0),       # 1s，硬切
    ("A6", 0),       # 1.5s 黑屏，硬切
    ("S02", 0.3),    # 3.5s，黑延长到3.3s（动作从容）
    ("S03", 0.25),   # 4s
    ("S04", 0.25),   # 4s
    ("S05", 0.15),   # 7s，奇观短叠化
    ("S07", 0.25),   # 5.5s
    ("S08", 0.25),   # 3.5s
    ("S09", 0.15),   # 6.5s，奇观最近
    ("S10", 0.25),   # 7.5s
    ("S11", 0.2),    # 4s
    ("S12", 0.1),    # 4s
    ("S13", 0.1),    # 4s，奇观
    ("S14", 0.2),    # 2.5s
    ("S15", 0.25),   # 4.5s
    ("S15_freeze", 0.2), # 定格 1.5s，稍微长叠化
]

# 所有片段归一化（已在之前的代码做过了，但再确认一遍）
norm_files = {}
for cid, _ in clip_order:
    if cid == "A6":
        src = os.path.join(CLIPS, "A6_clip.mp4")
    elif cid == "A4":
        src = os.path.join(CLIPS, "A4_clip_fast.mp4")
    elif cid == "S15_freeze":
        src = os.path.join(CLIPS, "S15_freeze.mp4")
    else:
        src = os.path.join(CLIPS, f"{cid}_clip.mp4")
    dst = os.path.join(NORM, f"{cid}_fade.mp4")
    norm_files[cid] = dst

print("=== 对每个片段首尾加 fade ===")
for cid, _, _ in clip_order:
    if cid == "A6":
        src = os.path.join(CLIPS, "A6_clip.mp4")
    elif cid == "A4":
        src = os.path.join(CLIPS, "A4_clip_fast.mp4")
    elif cid == "S15_freeze":
        src = os.path.join(CLIPS, "S15_freeze.mp4")
    else:
        src = os.path.join(CLIPS, f"{cid}_clip.mp4")
    dst = norm_files[cid]

    # 先去掉首尾的 0.05s（不需要开头淡入，避免开头过暗）
    # 尾部 fade out：前 N-0.2s 是正常画面，最后 fade_out_duration=0.2s 淡出
    dur = get_dur(src)
    fade_len = 0.2

    # 如果只剩 0.2s，直接全段暗一下（避免危险）
    if dur <= fade_len + 0.05:
        ff(["ffmpeg", "-y", "-i", src,
            "-vf", f"fade=t=out:st={max(0, dur - fade_len)}:d={fade_len},eq=brightness=-0.1",
            "-an",
            dst])
    else:
        # 去掉前面的淡入段（如果有），集中在尾
        # 第一步：filter_chain: 先 cut tail
        base_vid = dst
        cmd = ["ffmpeg", "-y",
               "-i", src,
               "-vf", f"trim=end={max(0.05, dur - fade_len)},setpts=PTS-STARTPTS",
               "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
               "-pix_fmt", "yuv420p", base_vid]
        if not os.path.exists(base_vid):
            ff(cmd)
            print(f"  {cid}: 去尾部 {fade_len}s 完成")
        else:
            print(f"  {cid}: 已存在")

        # 第二步：在片段尾加 fade out
        ff(["ffmpeg", "-y",
            "-i", base_vid,
            "-vf", f"fade=t=out:st=0:d={fade_len}",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", dst])
        print(f"  {cid}: 尾淡出 {fade_len}s 完成")

# 准备 concat 文件列表
concat_list = []
dur_sum = 0
for cid, _, _ in clip_order:
    src = norm_files[cid]
    dur_sum += get_dur(src)
    concat_list.append(src)

print(f"\n总时长(无重叠): {dur_sum:.2f}s")

# 写 concat 文件
concat_file = os.path.join(TMP, "concat_list.txt")
with open(concat_file, "w", encoding="utf-8") as f:
    for p in concat_list:
        f.write(f"file '{p}'\n")

# concat 合并
video_only = os.path.join(TMP, "video_only.mp4")
cmd = ["ffmpeg", "-y",
       "-f", "concat", "-safe", "0", "-i", concat_file,
       "-c:v", "libx264", "-preset", "medium", "-crf", "18",
       "-pix_fmt", "yuv420p", "-r", "24",
       video_only]
print("\nconcat 合并...")
ff(cmd)

vd = get_dur(video_only)
print(f"完成: {vd:.2f}s  {os.path.getsize(video_only)/1024/1024:.1f}MB")