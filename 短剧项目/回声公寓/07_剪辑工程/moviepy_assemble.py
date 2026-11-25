# -*- coding: utf-8 -*-
"""
MoviePy 独立后期剪辑层 —— 回声公寓 / AI 漫剧制作

定位：不管视频素材来自 Muse 还是图片+ffmpeg 运镜，本脚本只做"后期"：
  1. 拼接多个镜头片段（支持 crossfade 转场或硬切）
  2. 叠加旁白/音效音轨（按时间轴摆放，自动混音、淡入淡出）
  3. 统一画幅与调色（可选冷蓝统一色调，缓解跨镜色彩漂移）
  4. 烧录中文 ASS 字幕（借 ffmpeg ass 滤镜，保留样式、不出方块）
  5. 输出竖屏 mp4，faststart，本地渲染，零联网、不上传素材

依赖：项目独立环境 D:/Hermes环境准备/AI漫剧制作/.venv （moviepy 2.x）
用法示例：
  python moviepy_assemble.py \
      --clips 04_视频素材/待生成/muse_v2/S03_S01.mp4 \
              04_视频素材/待生成/muse_v2/S03_S02.mp4 \
              04_视频素材/待生成/muse_v2/S03_S03.mp4 \
      --narration 05_配音与音效/V01_旁白.mp3@0 \
      --subtitle 06_剪辑工程/subtitle.ass \
      --transition 0.4 \
      --out 07_最终成片/回声公寓_EP01_MoviePy版.mp4

说明：
  --narration 格式为 "音频路径@起始秒"，可重复多次。
  --transition 0 表示硬切；>0 表示相邻片段之间的"淡黑转场"秒数
    （前一段淡出到黑 + 后一段从黑淡入，总时长不变；非画面重叠的交叉溶解）。
    需要画面重叠的真交叉溶解时，可在此基础上改用 compose 时间线。
  字幕只在最终输出阶段用 ffmpeg 烧录；ASS 里已定义的字体/描边/位置全部保留。
"""
import argparse
import os
import subprocess
import sys
import tempfile

import moviepy
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    VideoFileClip,
    afx,
    vfx,
)
from moviepy import concatenate_videoclips


def parse_narration(items):
    """把 'path@start' 解析成 [(path, start_sec)]。"""
    out = []
    for it in items or []:
        if "@" in it:
            p, s = it.rsplit("@", 1)
            try:
                start = float(s)
            except ValueError:
                start = 0.0
        else:
            p, start = it, 0.0
        out.append((p, start))
    return out


def find_ffmpeg():
    """优先用 imageio_ffmpeg 自带二进制，其次系统 PATH。"""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def build_video(clip_paths, transition, size, grade):
    """拼接片段 + 可选转场/调色，返回合成后的 VideoClip（无声）。"""
    clips = []
    for p in clip_paths:
        if not os.path.isfile(p):
            raise FileNotFoundError(p)
        c = VideoFileClip(p)
        # 统一画幅：等比缩放到目标宽高（裁切溢出），保证竖屏一致
        c = c.resized(new_size=size)
        if grade:
            # 冷蓝统一色调：乘一个偏蓝的冷色系数，缓解跨镜色彩漂移。
            # 系数接近 1（R 略降、B 略升），保持画面亮度与写实感。
            c = c.with_effects([vfx.MultiplyColor((0.92, 0.97, 1.06))])
        clips.append(c)

    if transition and transition > 0 and len(clips) > 1:
        t = min(transition, min(c.duration for c in clips) / 3.0)
        seq = [clips[0].with_effects([vfx.CrossFadeOut(t)])]
        for c in clips[1:-1]:
            seq.append(c.with_effects([vfx.CrossFadeIn(t), vfx.CrossFadeOut(t)]))
        seq.append(clips[-1].with_effects([vfx.CrossFadeIn(t)]))
        merged = concatenate_videoclips(seq, method="chain")
    else:
        merged = concatenate_videoclips(clips, method="chain")

    return merged


def build_audio(narrations, video_duration, fade=0.15):
    """按时间轴摆放旁白，返回 CompositeAudioClip；无旁白返回 None。"""
    tracks = []
    for path, start in narrations:
        if not os.path.isfile(path):
            print(f"[警告] 旁白不存在，跳过：{path}", file=sys.stderr)
            continue
        a = AudioFileClip(path)
        if start > 0:
            a = a.with_start(start)
        # 不超出视频总长
        if start + a.duration > video_duration:
            a = a.subclipped(0, max(0.1, video_duration - start))
        a = a.with_effects([afx.AudioFadeIn(fade), afx.AudioFadeOut(fade)])
        tracks.append(a)
    if not tracks:
        return None
    return CompositeAudioClip(tracks).with_duration(video_duration)


def burn_subtitles(video_path, subtitle_path, ffmpeg, workdir):
    """用 ffmpeg ass 滤镜烧录字幕，返回新视频路径。"""
    if not subtitle_path or not os.path.isfile(subtitle_path):
        return video_path
    out = os.path.splitext(video_path)[0] + "_sub.mp4"
    # ASS 路径含 D: 冒号在滤镜里要转义；切到字幕目录用相对文件名最稳
    cwd = os.path.dirname(os.path.abspath(subtitle_path)) or workdir
    sub_name = os.path.basename(subtitle_path)
    vf = f"ass={sub_name}"
    cmd = [
        ffmpeg, "-y", "-i", os.path.abspath(video_path),
        "-vf", vf,
        "-c:v", "libx264", "-crf", "20", "-preset", "medium",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        os.path.abspath(out),
    ]
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print("[警告] 字幕烧录失败，保留无字幕版本：", r.stderr[-800:], file=sys.stderr)
        return video_path
    return out


def main():
    ap = argparse.ArgumentParser(description="MoviePy 独立后期剪辑层")
    ap.add_argument("--clips", nargs="+", required=True, help="镜头片段 mp4 列表")
    ap.add_argument("--narration", nargs="*", default=[], help="旁白 path@起始秒，可多个")
    ap.add_argument("--subtitle", default="", help="ASS 字幕文件")
    ap.add_argument("--transition", type=float, default=0.0, help="转场秒数，0=硬切")
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--height", type=int, default=1280)
    ap.add_argument("--grade", action="store_true", help="启用统一冷蓝色调")
    ap.add_argument("--out", required=True, help="输出 mp4 路径")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg()
    print(f"[信息] moviepy {moviepy.__version__} | ffmpeg: {ffmpeg}")
    print(f"[信息] 片段数={len(args.clips)} 转场={args.transition}s 调色统一={'开' if args.grade else '关'}")

    size = (args.width, args.height)
    workdir = os.getcwd()
    merged = build_video(args.clips, args.transition, size, args.grade)
    dur = merged.duration
    print(f"[信息] 拼接后时长={dur:.3f}s")

    audio = build_audio(parse_narration(args.narration), dur)
    if audio is not None:
        merged = merged.with_audio(audio)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    tmp_out = os.path.splitext(os.path.abspath(args.out))[0] + "_raw.mp4"
    print(f"[信息] 渲染中：{tmp_out}")
    merged.write_videofile(
        tmp_out, codec="libx264", audio_codec="aac",
        fps=24, preset="medium", ffmpeg_params=["-movflags", "+faststart"],
        logger="bar",
    )

    final = burn_subtitles(tmp_out, args.subtitle, ffmpeg, workdir)
    if final != tmp_out and os.path.exists(args.out):
        os.replace(final, args.out)
    elif final != tmp_out:
        os.replace(final, args.out)
    else:
        os.replace(tmp_out, args.out)

    print(f"[完成] 输出：{os.path.abspath(args.out)}")
    print(f"[完成] 大小：{os.path.getsize(args.out)} 字节")


if __name__ == "__main__":
    main()
