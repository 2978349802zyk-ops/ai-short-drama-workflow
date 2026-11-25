# -*- coding: utf-8 -*-
"""
EP01 15 秒投流测试片（D 阶段）
两条版本，只换钩子类型，其余素材/音效/参数一致，便于对比留存：
  A「镜像钩子」= 反常识 + 身份反转（门里站着一个我）
  B「危机钩子」= 冲突前置（出门接水的功夫，屋里的灯自己亮了）
零生成成本：全部复用 06_视频素材 + tmp_v5/sfx 已有音效 + 已有配音。
输出：EP01_测试片_A_镜像钩子.mp4 / EP01_测试片_B_危机钩子.mp4（720x1280 24fps 带字幕）
"""
import subprocess, os, json, shutil

BASE = "D:/Hermes环境准备/AI漫剧制作/短剧项目/回声公寓"
SRC = f"{BASE}/06_视频素材"
VO = f"{BASE}/05_配音与音效/EP01_v2_Serena_去电音"
SFX = f"{BASE}/07_剪辑工程/tmp_v5/sfx"
WORK = f"{BASE}/07_剪辑工程/tmp_test15"
OUTDIR = f"{BASE}/07_剪辑工程"
FF = "ffmpeg"
SR = 44100
MIN_XF = 1.0 / 24

# 字体不能用绝对路径：drawtext 的 fontfile 会把 "C:" 的冒号当参数分隔符
# 一律复制到工作目录、用相对路径（脚本 cwd = 07_剪辑工程）
os.makedirs(WORK, exist_ok=True)
_font_src = "C:/Windows/Fonts/simhei.ttf"
_font_dst = f"{WORK}/simhei.ttf"
if not os.path.exists(_font_dst):
    shutil.copy(_font_src, _font_dst)
os.chdir(OUTDIR)                      # 让相对字体路径稳定可用
FONT = "tmp_test15/simhei.ttf"

ENC_V = ["-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", "-r", "24", "-an"]

GRADE_COOL = "eq=brightness=-0.05:contrast=1.10:saturation=0.85,colorbalance=bs=0.06"
GRADE_WARM = "eq=brightness=-0.03:contrast=1.10:saturation=0.92,colorbalance=rs=0.04:gs=0.02"
FULL_CROP = "crop=iw*0.98:ih*0.98:(iw*0.02)/2:(ih*0.02)/2,scale=720:1280:flags=lanczos"
DELOGO = "delogo=x=296:y=1012:w=136:h=96"   # S10 底部 AI 乱码水印
# S11 底部左下角有残留 AI 乱码：裁掉底 10%（保持 9:16，等效轻微推近）
CROP_BOTTOM = "crop=648:1152:36:0,scale=720:1280:flags=lanczos"

# 每版最终响度增益（dB），配 compand 手机外放曲线，实测对齐 -16 LUFS
FINAL_GAIN = {"A_镜像钩子": 0.7, "B_危机钩子": 0.8}   # tinn 降电平+母版谱减后重测   # 补全 6 句配音后重测的增益
COMPAND = "compand=attacks=0:decays=0.3:points=-80/-70|-25/-14|-10/-6|0/-3"
LIMIT = "alimiter=level=disabled:limit=0.85:attack=5:release=60"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2500:])
        raise RuntimeError("ffmpeg failed: " + " ".join(cmd[:10]))
    return r


def dur_of(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", p],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def sub_filter(text, size=42, y_off=0):
    """白字 + 黑描边 + 半透明底，居中偏下；0.12s 淡入"""
    t = text.replace("'", "").replace(":", "，").replace("%", "％")
    return (
        f"drawtext=fontfile={FONT}:text='{t}':fontsize={size}:fontcolor=white:"
        f"borderw=3:bordercolor=black@0.85:box=1:boxcolor=black@0.35:boxborderw=10:"
        f"x=(w-text_w)/2:y=h-{260 + y_off}:"
        f"alpha='if(lt(t,0.12),t/0.12,1)'"
    )


def make_clip(dst, tag, ss, dur, vf_chain):
    cmd = [FF, "-y", "-ss", str(ss), "-t", str(dur), "-i", f"{SRC}/EP01_{tag}.mp4",
           "-vf", ",".join(vf_chain)] + ENC_V + [dst]
    run(cmd)


def make_title_card(dst, sec, line1, line2, line3):
    d = (f"drawtext=fontfile={FONT}:text='{line1}':fontsize=96:fontcolor=white:"
         f"x=(w-text_w)/2:y=470:alpha='if(lt(t,0.15),t/0.15,1)',"
         f"drawtext=fontfile={FONT}:text='{line2}':fontsize=44:fontcolor=0xE8D9B0:"
         f"x=(w-text_w)/2:y=620:alpha='if(lt(t,0.35),0,if(lt(t,0.7),(t-0.35)/0.35,1))',"
         f"drawtext=fontfile={FONT}:text='{line3}':fontsize=34:fontcolor=0x9A9A9A:"
         f"x=(w-text_w)/2:y=1050:alpha='if(lt(t,0.6),0,if(lt(t,1.0),(t-0.6)/0.4,1))'")
    run([FF, "-y", "-f", "lavfi", "-i", f"color=c=black:s=720x1280:r=24:d={sec}",
         "-vf", d] + ENC_V + [dst])


def join_xfade(files, dst):
    """全链 xfade；硬切位置用 1 帧交叉（小于一帧会让输出长度塌陷）"""
    if len(files) == 1:
        shutil.copy(files[0], dst)
        return
    inputs = []
    for f in files:
        inputs += ["-i", f]
    durs = [dur_of(f) for f in files]
    parts, prev = [], "[0:v]"
    off = 0.0
    for i in range(1, len(files)):
        off += durs[i - 1] - MIN_XF
        lbl = f"[v{i}]"
        parts.append(f"{prev}[{i}:v]xfade=transition=fade:duration={MIN_XF:.4f}:offset={off:.4f}{lbl}")
        prev = lbl
    fc = ";".join(parts)
    run([FF, "-y", *inputs, "-filter_complex", fc, "-map", prev] + ENC_V + [dst])


# 耳鸣音收窄到 1.5–4.2 kHz 并压电平：原本 2.5–5 kHz 的噪声在手机外放上听成「沙沙杂音」
SFX_FILTER = {"tinn": "highpass=f=1500,lowpass=f=4200"}
# 母版收尾：轻度谱减 + 切掉 15 kHz 以上（噪声床与 AAC 的毛刺都在这一带）
MASTER_FIX = "afftdn=nr=6:nf=-50,lowpass=f=15000"


def build_audio(dst, total, vo_items, sfx_items, use_bgm_mid):
    """vo_items: [(wav, at, gain)]  sfx_items: [(name, at, gain)]  BGM 分层"""
    inputs, chains, mix = [], [], []
    idx = 0

    # BGM 底噪：全程低频 +（可选）中段氛围
    inputs += ["-i", f"{SFX}/bgm_low.wav"]
    chains.append(f"[{idx}:a]volume=0.30,atrim=0:{total},afade=t=in:st=0:d=1.2,"
                  f"afade=t=out:st={total-1.0:.2f}:d=1.0[b0]")
    mix.append("[b0]")
    idx += 1
    if use_bgm_mid:
        inputs += ["-i", f"{SFX}/bgm_mid.wav"]
        chains.append(f"[{idx}:a]volume=0.22,atrim=0:{total},"
                      f"afade=t=in:st=0:d=1.5,afade=t=out:st={total-1.2:.2f}:d=1.2[b1]")
        mix.append("[b1]")
        idx += 1

    for wav, at, gain in vo_items:
        inputs += ["-i", wav]
        ms = int(at * 1000)
        chains.append(f"[{idx}:a]volume={gain},adelay={ms}|{ms},"
                      f"aformat=sample_fmts=fltp:channel_layouts=mono[v{idx}]")
        mix.append(f"[v{idx}]")
        idx += 1

    for name, at, gain in sfx_items:
        p = f"{SFX}/{name}.wav"
        inputs += ["-i", p]
        ms = int(at * 1000)
        pre = SFX_FILTER.get(name, "")
        pre = f"{pre}," if pre else ""
        chains.append(f"[{idx}:a]{pre}volume={gain},adelay={ms}|{ms},"
                      f"aformat=sample_fmts=fltp:channel_layouts=mono[s{idx}]")
        mix.append(f"[s{idx}]")
        idx += 1

    fc = ";".join(chains) + ";" + "".join(mix) + \
        f"amix=inputs={len(mix)}:normalize=0:dropout_transition=0," \
        f"{MASTER_FIX},alimiter=level=disabled:limit=0.85,atrim=0:{total}," \
        f"aformat=sample_fmts=s16:channel_layouts=mono[aout]"
    run([FF, "-y", *inputs, "-filter_complex", fc, "-map", "[aout]",
         "-ar", str(SR), "-c:a", "pcm_s16le", dst])


def mux(v, a, dst):
    run([FF, "-y", "-i", v, "-i", a, "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-ac", "1",
         "-movflags", "+faststart", dst])


# ============================================================
# 版本定义
# ============================================================
A_CLIPS = [
    # (key, tag, ss, dur, grade, vf_extra, subtitle)
    ("a1", "S05", 1.8, 2.2, GRADE_WARM, None, "302，三年没人住过"),
    ("a2", "S10", 0.6, 2.4, GRADE_COOL, DELOGO, "今晚，门缝里站着另一个我"),
    ("a3", "S09", 1.2, 2.2, GRADE_WARM, None, "我抬手，她也抬手"),
    ("a4", "S13", 0.4, 2.4, GRADE_WARM, None, "一样的脸，连声音都一样"),
    ("a5", "S11", 0.2, 2.4, GRADE_COOL, CROP_BOTTOM, "到底哪个才是我"),
    ("a6", "S14", 0.6, 2.0, GRADE_COOL, None, "转身跑，她还在门里"),
]
A_TAIL = 1.4
# 6 条字幕全部配同音色 Serena（qwen3-tts-06cv），裁静音+变速塞进各自镜头
FIT = f"{WORK}/vo/fit"
A_VO = [(f"{FIT}/A1.wav", 0.05, 1.00),
        (f"{FIT}/A2.wav", 2.21, 1.00),
        (f"{FIT}/A3.wav", 4.57, 1.00),
        (f"{FIT}/A4.wav", 6.73, 1.00),
        (f"{FIT}/A5.wav", 9.08, 1.05),
        (f"{FIT}/A6.wav", 11.44, 1.00)]
A_SFX = [("tinn", 0.0, 0.35), ("thump", 0.0, 0.5), ("heart", 2.2, 0.55),
         ("heart", 3.0, 0.55), ("click", 4.5, 0.7), ("riser", 6.6, 0.55),
         ("knock", 9.2, 0.85), ("knock", 9.62, 0.8), ("step", 11.7, 0.7),
         ("step", 12.05, 0.7), ("whoosh", 13.2, 0.6)]

B_CLIPS = [
    ("b1", "S08", 0.3, 2.0, GRADE_COOL, None, "出门接水时，灯是关的"),
    ("b2", "S05", 2.4, 2.2, GRADE_WARM, None, "可门缝里，有光"),
    ("b3", "S06", 5.6, 2.2, GRADE_WARM, "crop=200:356:440:200,scale=720:1280:flags=lanczos",
     "还有一双眼睛，在往外看"),
    ("b4", "S10", 1.2, 2.6, GRADE_COOL, DELOGO, "她长得，和我一模一样"),
    ("b5", "S11", 0.2, 2.4, GRADE_COOL, CROP_BOTTOM, "你到底想干什么"),
    ("b6", "S13", 1.6, 2.0, GRADE_WARM, None, "门，自己开了"),
]
B_TAIL = 1.6
B_VO = [(f"{FIT}/B1.wav", 0.05, 1.00),
        (f"{FIT}/B2.wav", 2.01, 1.00),
        (f"{FIT}/B3.wav", 4.17, 1.00),
        (f"{FIT}/B4.wav", 6.33, 1.00),
        (f"{FIT}/B5.wav", 8.88, 1.00),
        (f"{FIT}/B6.wav", 11.24, 1.00)]
B_SFX = [("thump", 0.0, 0.7), ("water", 0.4, 0.35), ("tinn", 2.0, 0.32),
         ("breath", 4.2, 0.7), ("riser", 6.4, 0.6), ("knock", 9.0, 0.8),
         ("knock", 9.42, 0.75), ("creak", 11.4, 0.8), ("whoosh", 13.4, 0.55)]


def build(version, clips, tail, vo, sfx, title_lines):
    outdir = f"{WORK}/{version}"
    os.makedirs(outdir, exist_ok=True)
    files = []
    for key, tag, ss, d, grade, extra, sub in clips:
        vf = []
        vf.append(extra if extra and extra.startswith("crop=") else FULL_CROP)
        vf.append(grade)
        if extra and extra.startswith("delogo"):
            vf.append(extra)
        if extra and "scale=720:1280" in extra:
            pass  # 已自带 scale
        vf.append(sub_filter(sub))
        dst = f"{outdir}/{key}.mp4"
        make_clip(dst, tag, ss, d, vf)
        files.append(dst)
        print("  ", key, tag, f"{d}s", "OK")

    # 片名卡
    card = f"{outdir}/card.mp4"
    make_title_card(card, tail, title_lines[0], title_lines[1], title_lines[2])
    files.append(card)

    video = f"{outdir}/video.mp4"
    join_xfade(files, video)
    total = dur_of(video)

    audio = f"{outdir}/audio.wav"
    build_audio(audio, total, vo, sfx, use_bgm_mid=True)

    dst = f"{OUTDIR}/EP01_测试片_{version}.mp4"
    mux(video, audio, dst)

    # 最后一关：响度对齐（从 audio.wav 母版做，视频纯拷贝，不重编码）
    g = FINAL_GAIN[version]
    raw = f"{outdir}/_mux_raw.mp4"
    shutil.move(dst, raw)
    run([FF, "-y", "-v", "error", "-i", raw, "-i", audio, "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-af", f"volume={g}dB,{COMPAND},{LIMIT}",
         "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-ac", "1",
         "-movflags", "+faststart", dst])
    os.remove(raw)
    print(">>>", dst, round(total, 3), "s")
    return dst, total


print("=== 版本 A：镜像钩子 ===")
build("A_镜像钩子", A_CLIPS, A_TAIL, A_VO, A_SFX,
      ("回声公寓", "第 1 集 · 门缝", "竖屏短剧 · 测试片 A"))

print("=== 版本 B：危机钩子 ===")
build("B_危机钩子", B_CLIPS, B_TAIL, B_VO, B_SFX,
      ("回声公寓", "第 1 集 · 门缝", "竖屏短剧 · 测试片 B"))
print("ALL DONE")
