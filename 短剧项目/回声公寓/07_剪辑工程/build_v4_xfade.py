"""
EP01 精剪 v4 构建脚本 — 视频拼接（增量式 xfade）
将所有片段用增量方式逐个 xfade 拼接，避免一个巨大 filter_complex 出问题
"""
import subprocess
import os

BASE = "D:/Hermes环境准备/AI漫剧制作/短剧项目/回声公寓"
OUT = f"{BASE}/07_剪辑工程/tmp_v4/clips"
TMP = f"{BASE}/07_剪辑工程/tmp_v4"
FINAL_VIDEO = f"{TMP}/EP01_v4_video.mp4"

FF = "ffmpeg"


def run(cmd):
    print(" ".join(cmd[:8]) + " ..." if len(cmd) > 8 else " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2000:])
        raise RuntimeError("ffmpeg failed")
    return r


def get_dur(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


# 片段顺序和叠化时长（与 build_v4_video.py 一致）
clips_info = [
    ("A1_eye.mp4", 0),
    ("A2_face.mp4", 0),
    ("A3_blink.mp4", 0),
    ("A4_door.mp4", 0.15),
    ("A5_dark.mp4", 0.3),
    ("A6_black.mp4", 0.3),
    ("01_S02.mp4", 0.0),
    ("02_S03.mp4", 0.25),
    ("03_S04.mp4", 0.20),
    ("04_S05.mp4", 0.10),
    ("05_S06.mp4", 0.25),
    ("06_S07.mp4", 0.30),
    ("07_S08.mp4", 0.25),
    ("08_S09.mp4", 0.10),
    ("09_S10.mp4", 0.25),
    ("10_S11a.mp4", 0.20),
    ("10_S11b.mp4", 0.0),
    ("11_S12.mp4", 0.20),
    ("12_S13.mp4", 0.10),
    ("13_S14.mp4", 0.25),
    ("14_S15a.mp4", 0.20),
    ("14_S15b.mp4", 0.15),
]

print("=== 增量式 xfade 拼接 ===")

# 验证所有片段存在
for fname, _ in clips_info:
    p = f"{OUT}/{fname}"
    if not os.path.exists(p):
        print(f"  MISSING: {p}")
    else:
        d = get_dur(p)
        print(f"  {fname}: {d:.3f}s")

# 增量拼接
current = f"{OUT}/{clips_info[0][0]}"
current_dur = get_dur(current)

for i in range(1, len(clips_info)):
    next_file = f"{OUT}/{clips_info[i][0]}"
    xfade_dur = clips_info[i][1]
    next_dur = get_dur(next_file)

    if xfade_dur <= 0:
        # 硬切：直接 concat（用 concat demuxer 快速处理）
        concat_list = f"{TMP}/concat_tmp.txt"
        with open(concat_list, "w") as f:
            f.write(f"file '{current}'\n")
            f.write(f"file '{next_file}'\n")
        out_file = f"{TMP}/build_{i:02d}.mp4"
        cmd = [FF, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
               "-c", "copy", "-an", out_file]
        run(cmd)
        new_dur = current_dur + next_dur
    else:
        # xfade 叠化
        offset = current_dur - xfade_dur
        out_file = f"{TMP}/build_{i:02d}.mp4"
        cmd = [FF, "-y",
               "-i", current,
               "-i", next_file,
               "-filter_complex",
               f"[0:v][1:v]xfade=transition=fade:duration={xfade_dur}:offset={offset}[outv]",
               "-map", "[outv]",
               "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24", "-an",
               out_file]
        run(cmd)
        new_dur = current_dur + next_dur - xfade_dur

    print(f"  + {clips_info[i][0]} (xfade={xfade_dur}s) → 累计 {new_dur:.3f}s")
    current = out_file
    current_dur = new_dur

# 最终文件
import shutil
shutil.copy2(current, FINAL_VIDEO)

actual_dur = get_dur(FINAL_VIDEO)
print(f"\n视频总时长: {actual_dur:.3f} 秒")
print(f"视频输出: {FINAL_VIDEO}")
