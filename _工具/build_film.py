# -*- coding: utf-8 -*-
"""生产主线脚本 · 《回声公寓》EP01 样片（图 + 运镜 + 配音 + 字幕 -> 成片）

职责（对应「制作流程」阶段 6~9）：
  1. 读 02_分镜与提示词/分镜表.csv，校验 6 镜镜号；
  2. 每镜：场景静图 + ffmpeg zoompan 运镜 + 对应配音/静音音轨 -> 04_视频镜头/已生成/EP01_Sx.mp4；
  3. concat 六镜（06_剪辑工程/concat_list.txt）-> 临时全片；
  4. 全片 loudnorm 响度归一到 -16 LUFS + -movflags +faststart -> 07_最终成片/回声公寓_EP01_样片_v01.mp4；
  5. 验收：ffprobe 元数据 / 全解码 error 计数 / 抽帧 YAVG / freezedetect / LUFS / box 顺序（moov 在前）。

用法:
  python build_film.py --smoke          只渲染 S1 到临时目录做技术冒烟（不覆盖正式产物）
  python build_film.py                  全流程出片
  python build_film.py --verify-only    只对已有成片做验收

设计说明（不擅自扩范围）：
  - 本机未配置图生视频大模型，muse.ai 接入留空；按试制计划用「静图 + ffmpeg zoompan 运镜」替代，
    运镜幅度 1.0~1.15（见提示词规范「zoompan 控制在 1.05~1.15」，急停镜最高 1.15）。
  - 时长按旁白字数 4.5 字/秒 + 留白估算，6 镜合计 24.0s，落在试制计划「约 24 秒」。
  - 字幕只落有旁白的 S1、S6 两句（S3/S4 是音效，不配字幕）。
"""
import csv
import glob
import os
import shutil
import subprocess
import sys

ROOT = r"D:/Hermes环境准备/AI漫剧制作"
D_CSV = os.path.join(ROOT, "02_分镜与提示词", "分镜表.csv")
D_SCENE = os.path.join(ROOT, "03_角色与场景素材", "场景")
D_SHOT = os.path.join(ROOT, "04_视频镜头", "已生成")
D_VOICE = os.path.join(ROOT, "05_配音与音效")
D_EDIT = os.path.join(ROOT, "06_剪辑工程")
D_FINAL = os.path.join(ROOT, "07_最终成片")
D_TMP = os.path.join(D_EDIT, "tmp")

W, H, FPS = 1080, 1920, 24
FINAL_NAME = "回声公寓_EP01_样片_v01.mp4"

# 每镜：(序号, 时长秒, 运镜类型, 字幕文本)
#  时长：旁白/音效 + 留白估算；运镜类型映射自「分镜表.镜头运动」列；字幕取有旁白的两句。
PLAN = [
    (1, 4.0, "push_in",        "整栋楼都睡了"),          # S1 缓慢推轨推进
    (2, 3.5, "static_push",    None),                    # S2 固定机位轻微前推
    (3, 4.0, "fast_push_stop", None),                    # S3 快速推近后急停
    (4, 4.5, "handheld",       None),                    # S4 手持轻晃
    (5, 3.5, "tilt_down",      None),                    # S5 缓慢下摇
    (6, 4.5, "slow_push",      "门后没人，那只手是谁的？"),  # S6 极缓慢推近 + 字幕
]

FONT = None


def find_font():
    for cand in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "msyh.ttf", "simsun.ttc"):
        p = os.path.join(r"C:/Windows/Fonts", cand)
        if os.path.isfile(p):
            return p
    raise SystemExit("未找到中文字体（msyh.ttc / simhei.ttf ...），drawtext 无法生成中文")


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("PATH 上找不到 ffmpeg")
    return exe


def ffprobe():
    exe = shutil.which("ffprobe")
    if not exe:
        raise SystemExit("PATH 上找不到 ffprobe")
    return exe


def run(args, tag=""):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"[FAIL] {tag} rc={r.returncode}")
        print(r.stdout[-2000:])
        print(r.stderr[-3000:])
        raise SystemExit(1)
    return r


def scene_img(n):
    hits = sorted(glob.glob(os.path.join(D_SCENE, f"S{n:02d}_*.png")))
    if not hits:
        raise SystemExit(f"缺场景图: {D_SCENE}/S{n:02d}_*.png")
    return hits[0]


def voice_audio(n):
    hits = sorted(glob.glob(os.path.join(D_VOICE, f"V{n:02d}_*.mp3")))
    return hits[0] if hits else None


def zoompan_filter(mode, dur):
    """按运镜类型构造 zoompan 参数。d=总帧数；on=输出帧号。"""
    fr = max(int(round(dur * FPS)), 2)
    dmax = fr - 1
    cx = "iw/2-(iw/zoom/2)"
    cy = "ih/2-(ih/zoom/2)"
    if mode == "push_in":               # 缓慢推近 1.0 -> 1.10
        z = f"min(1+0.10*on/{dmax},1.10)"
        x, y = cx, cy
    elif mode == "static_push":         # 固定机位轻微前推 1.02 -> 1.06
        z = f"min(1.02+0.04*on/{dmax},1.06)"
        x, y = cx, cy
    elif mode == "fast_push_stop":      # 前 35% 冲到 1.15 后急停
        hold = max(int(round(fr * 0.35)), 2)
        z = f"if(lt(on,{hold}),1+0.15*on/{hold},1.15)"
        x, y = cx, cy
    elif mode == "handheld":            # 固定 1.08 + 微抖（手持感）
        z = "1.08"
        x = f"iw/2-(iw/zoom/2)+6*sin(on*0.8)"
        y = f"ih/2-(ih/zoom/2)+5*cos(on*0.9)"
    elif mode == "tilt_down":           # 固定 1.12，画面自上而下摇
        z = "1.12"
        x = cx
        y = f"(ih-ih/zoom)*on/{dmax}"
    elif mode == "slow_push":           # 极缓慢推近 1.0 -> 1.05
        z = f"min(1+0.05*on/{dmax},1.05)"
        x, y = cx, cy
    else:
        raise SystemExit(f"未知运镜类型: {mode}")
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={fr}:s={W}x{H}:fps={FPS}"


def drawtext_filter(text):
    if not text:
        return ""
    font_esc = FONT.replace(":", r"\:")
    # 中文标点（，？）非 filtergraph 分隔符，可直接放进 text
    return (
        f",drawtext=fontfile='{font_esc}':text='{text}':"
        f"fontcolor=white:fontsize=44:borderw=3:bordercolor=black@0.85:"
        f"box=1:boxcolor=black@0.42:boxborderw=16:"
        f"x=(w-text_w)/2:y=h*0.80"
    )


def render_shot(n, dur, mode, subtitle, outdir):
    img = scene_img(n)
    aud = voice_audio(n)
    out = os.path.join(outdir, f"EP01_S{n}.mp4")
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"{zoompan_filter(mode, dur)},setsar=1"
        f"{drawtext_filter(subtitle)},format=yuv420p"
    )
    af = (f"apad,atrim=0:{dur},asetpts=N/SR/TB,"
          f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo")
    args = [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", img]
    if aud:
        args += ["-i", aud]
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    args += [
        "-filter_complex", f"[0:v]{vf}[v];[1:a]{af}[a]",
        "-map", "[v]", "-map", "[a]",
        "-t", f"{dur}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", out,
    ]
    run(args, tag=f"渲染 S{n}")
    return out


def box_order(path):
    """读 mp4 顶层 box 顺序，判断 moov 是否在 mdat 之前（faststart）。"""
    order = []
    with open(path, "rb") as f:
        size = os.path.getsize(path)
        pos = 0
        while pos + 8 <= size:
            f.seek(pos)
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            bsize = int.from_bytes(hdr[:4], "big")
            btype = hdr[4:8].decode("latin1")
            order.append(btype)
            if bsize == 1:  # 64-bit largesize
                ext = f.read(8)
                bsize = int.from_bytes(ext, "big")
            if bsize <= 0:
                break
            pos += bsize
    return order


def probe_streams(path):
    r = run([ffprobe(), "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
             "-of", "default=noprint_wrappers=1", path], tag="ffprobe")
    return r.stdout.strip()


def yavg_at(path, t):
    r = subprocess.run(
        [ffmpeg(), "-hide_banner", "-ss", f"{t}", "-i", path, "-frames:v", "1",
         "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG",
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (r.stdout + r.stderr).splitlines():
        if "YAVG" in line:
            return line.split("=")[-1]
    return ""


def decode_errors(path):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-v", "error", "-i", path, "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return len([l for l in (r.stdout + r.stderr).splitlines() if l.strip()])


def freeze_count(path):
    r = subprocess.run(
        [ffmpeg(), "-hide_banner", "-nostats", "-i", path,
         "-vf", "freezedetect=n=0.003:d=0.5", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout + r.stderr).count("freeze_start")


def lufs(path):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    import re
    vals = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)", r.stdout + r.stderr)
    return vals[-1] if vals else ""


def verify(path):
    print(f"\n===== 验收 {os.path.basename(path)} =====")
    dur = None
    for line in probe_streams(path).splitlines():
        key, _, val = line.partition("=")
        if key.strip() == "duration":
            dur = float(val)
    print("[元数据]\n" + probe_streams(path))
    do = box_order(path)
    fast = ("moov" in do and "mdat" in do and do.index("moov") < do.index("mdat"))
    print(f"[box 顺序] {' -> '.join(do)}  => faststart={'是' if fast else '否'}")
    errs = decode_errors(path)
    print(f"[全解码] error 行计数 = {errs}")
    frz = freeze_count(path)
    print(f"[freezedetect] freeze_start 计数 = {frz}")
    lu = lufs(path)
    print(f"[响度] 积分 LUFS = {lu or '未取到'}")
    if dur:
        ratios = [0.12, 0.38, 0.5, 0.62, 0.88]
        seq = " / ".join(f"{t:.1f}s:{yavg_at(path, t)}" for t in ratios)
        print(f"[抽帧 YAVG] {seq}（黑屏<16，正常约 100-140）")
    ok = fast and errs == 0 and frz == 0
    print(f"[结论] {'PASS' if ok else 'FAIL'}  (faststart={fast}, decode_err={errs}, freeze={frz})")
    return ok


def main():
    global FONT
    FONT = find_font()
    print(f"字体: {FONT}")

    # 校验分镜表 6 镜存在
    with open(D_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    ids = [r[0] for r in rows[1:] if r and r[0].strip()]
    print(f"分镜表镜号: {ids}")
    if len(ids) != 6:
        raise SystemExit(f"分镜表应有 6 镜，实际 {len(ids)}")

    if "--verify-only" in sys.argv:
        final = os.path.join(D_FINAL, FINAL_NAME)
        sys.exit(0 if (os.path.isfile(final) and verify(final)) else 1)

    smoke = "--smoke" in sys.argv
    outdir = os.path.join(D_TMP, "smoke") if smoke else D_SHOT
    os.makedirs(outdir, exist_ok=True)

    if smoke:
        shots = [PLAN[0]]
        print("\n[smoak] 只渲染 S1")
    else:
        shots = PLAN

    outs = []
    for n, dur, mode, sub in shots:
        print(f"[渲染] S{n}  {dur}s  {mode}  字幕={'有' if sub else '无'}")
        outs.append(render_shot(n, dur, mode, sub, outdir))

    if smoke:
        print("\n[smoak] S1 验收：")
        sys.exit(0 if verify(outs[0]) else 1)

    # concat
    list_path = os.path.join(D_EDIT, "concat_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for o in outs:
            f.write(f"file '{o.replace(os.sep, '/')}'\n")
    tmp_all = os.path.join(D_TMP, "concat_noformat.mp4")
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", list_path,
         "-c", "copy", "-movflags", "+faststart", tmp_all], tag="concat")
    print(f"[拼接] {list_path} -> {tmp_all}")

    # 响度归一 + faststart 成片
    final = os.path.join(D_FINAL, FINAL_NAME)
    os.makedirs(D_FINAL, exist_ok=True)
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", tmp_all,
         "-c:v", "copy",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart", final], tag="最终成片")
    print(f"[成片] {final}")

    ok = verify(final)
    print("\n结果:", "通过" if ok else "未通过")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
