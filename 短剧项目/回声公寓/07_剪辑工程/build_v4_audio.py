"""
EP01 精剪 v4 构建脚本 — 下半部分：音效合成 + 完整音轨混音
三层音轨：配音 + 音效(SFX) + BGM
输出：EP01_精剪_v4_音轨.wav + EP01_精剪_v4.mp4（最终成片）

时间点基于 build_v4_xfade.py 的精确输出（79.158s）：
  蒙太奇结束(S02开始): ~5.083s
  S03 开始: ~10.042s
  S04 开始: ~12.050s
  S05 奇观1开始: ~15.658s
  S06 开始: ~25.450s
  S07 开始: ~28.983s
  S08 开始: ~37.067s
  S09 奇观2开始: ~42.008s
  S10 开始: ~51.967s
  S11a 开始: ~59.975s
  S11b 开始: ~62.058s
  S12 开始: ~63.608s
  S13 奇观3开始: ~67.508s
  S14 开始: ~71.258s
  S15a 开始: ~72.475s
  S15b 定格开始: ~77.158s
  总时长: ~79.158s
"""
import subprocess
import os

BASE = "D:/Hermes环境准备/AI漫剧制作/短剧项目/回声公寓"
VOICE_DIR = f"{BASE}/05_配音与音效/EP01_v2_Serena_去电音"
TMP = f"{BASE}/07_剪辑工程/tmp_v4"
SFX_DIR = f"{TMP}/sfx"
VIDEO_FILE = f"{TMP}/EP01_v4_video.mp4"
FINAL_AUDIO = f"{BASE}/07_剪辑工程/EP01_精剪_v4_音轨.wav"
FINAL_VIDEO = f"{BASE}/07_剪辑工程/EP01_精剪_v4.mp4"

os.makedirs(SFX_DIR, exist_ok=True)

FF = "ffmpeg"
SR = 44100  # 采样率


def run(cmd):
    print(" ".join(cmd[:6]) + " ..." if len(cmd) > 6 else " ".join(cmd))
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


# 获取视频总时长
TOTAL_DUR = get_dur(VIDEO_FILE)
print(f"视频总时长: {TOTAL_DUR:.3f}s")


# ============================================================
# 第一部分：合成基础音效
# ============================================================
print("=== Part 1: 合成基础音效 ===")

# 1. 低频嗡鸣（40Hz）— 10秒版本（开场用）
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=40:duration=10:sample_rate={SR},"
       f"volume=0.15,"
       f"lowpass=f=80,"
       f"tremolo=f=0.3:d=0.2",
       "-ac", "1", f"{SFX_DIR}/drone_40hz_10s.wav"]
run(cmd)

# 长版本（90秒）全片环境垫底
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=45:duration=90:sample_rate={SR},"
       f"volume=0.08,"
       f"lowpass=f=100,"
       f"tremolo=f=0.2:d=0.3",
       "-ac", "1", f"{SFX_DIR}/ambient_drone_90s.wav"]
run(cmd)

# 2. 单跳心跳
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=60:duration=0.2:sample_rate={SR},"
       f"volume=0.5,"
       f"afade=t=in:st=0:d=0.01,"
       f"afade=t=out:st=0.02:d=0.18",
       "-ac", "1", f"{SFX_DIR}/heartbeat_single.wav"]
run(cmd)


def make_heartbeat_seq(duration, bpm, out_path, volume=0.5, crescendo=False):
    """生成心跳序列"""
    interval = 60.0 / bpm
    n_beats = int(duration / interval) + 1
    filter_parts = []
    for i in range(n_beats):
        delay_ms = int(i * interval * 1000)
        vol = volume
        if crescendo:
            vol = volume * (0.3 + 0.7 * i / max(n_beats - 1, 1))
        filter_parts.append(
            f"sine=frequency=60:duration=0.2:sample_rate={SR},"
            f"volume={vol},"
            f"afade=t=in:st=0:d=0.01,"
            f"afade=t=out:st=0.02:d=0.18,"
            f"adelay={delay_ms}|{delay_ms}[b{i}]"
        )
    mix_inputs = "".join(f"[b{i}]" for i in range(n_beats))
    filter_parts.append(f"{mix_inputs}amix=inputs={n_beats}:duration=longest[out]")
    filter_complex = ";".join(filter_parts)
    cmd = [FF, "-y", "-filter_complex", filter_complex,
           "-map", "[out]", "-t", str(duration), "-ac", "1", out_path]
    run(cmd)


# 开场蒙太奇用心跳（渐强）
make_heartbeat_seq(4.0, 90, f"{SFX_DIR}/heartbeat_opening.wav", volume=0.6, crescendo=True)
# 结尾用心跳（快）
make_heartbeat_seq(3.0, 120, f"{SFX_DIR}/heartbeat_fast.wav", volume=0.4, crescendo=False)

# 3. 低频冲击音（咚）
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=80:duration=0.5:sample_rate={SR},"
       f"volume=0.7,"
       f"afade=t=in:st=0:d=0.005,"
       f"afade=t=out:st=0.05:d=0.45,"
       f"lowpass=f=200",
       "-ac", "1", f"{SFX_DIR}/thump_low.wav"]
run(cmd)

# 重冲击音（奇观/结尾）
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=50:duration=1.0:sample_rate={SR},"
       f"volume=0.8,"
       f"afade=t=in:st=0:d=0.01,"
       f"afade=t=out:st=0.1:d=0.9,"
       f"lowpass=f=150,"
       f"tremolo=f=5:d=0.5",
       "-ac", "1", f"{SFX_DIR}/thump_heavy.wav"]
run(cmd)

# 4. Whoosh（白闪/高频）
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"anoisesrc=color=white:duration=0.3:sample_rate={SR},"
       f"volume=0.4,"
       f"highpass=f=500,"
       f"lowpass=f=8000,"
       f"afade=t=in:st=0:d=0.01,"
       f"afade=t=out:st=0.1:d=0.2",
       "-ac", "1", f"{SFX_DIR}/whoosh_white.wav"]
run(cmd)

# 低频 whoosh（黑闪用）
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"anoisesrc=color=brown:duration=0.4:sample_rate={SR},"
       f"volume=0.5,"
       f"lowpass=f=500,"
       f"afade=t=in:st=0:d=0.01,"
       f"afade=t=out:st=0.15:d=0.25",
       "-ac", "1", f"{SFX_DIR}/whoosh_low.wav"]
run(cmd)

# 5. 嗒声（眼皮/轻响）
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=800:duration=0.05:sample_rate={SR},"
       f"volume=0.3,"
       f"afade=t=in:st=0:d=0.005,"
       f"afade=t=out:st=0.01:d=0.04",
       "-ac", "1", f"{SFX_DIR}/click_light.wav"]
run(cmd)

# 门锁咔哒
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=300:duration=0.1:sample_rate={SR},"
       f"volume=0.35,"
       f"afade=t=in:st=0:d=0.005,"
       f"afade=t=out:st=0.02:d=0.08,"
       f"lowpass=f=800",
       "-ac", "1", f"{SFX_DIR}/click_doorlock.wav"]
run(cmd)

# 6. 呼吸声
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"anoisesrc=color=pink:duration=1.5:sample_rate={SR},"
       f"volume=0.25,"
       f"lowpass=f=600,"
       f"highpass=f=100,"
       f"tremolo=f=0.7:d=0.6",
       "-ac", "1", f"{SFX_DIR}/breathing_15s.wav"]
run(cmd)

# 急促呼吸
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"anoisesrc=color=pink:duration=3.0:sample_rate={SR},"
       f"volume=0.35,"
       f"lowpass=f=800,"
       f"highpass=f=150,"
       f"tremolo=f=2.0:d=0.7",
       "-ac", "1", f"{SFX_DIR}/breathing_fast_3s.wav"]
run(cmd)

# 7. 脚步声
def make_footsteps(n_steps, out_path, interval=0.5, volume=0.2):
    filter_parts = []
    for i in range(n_steps):
        delay_ms = int(i * interval * 1000)
        filter_parts.append(
            f"sine=frequency=70:duration=0.12:sample_rate={SR},"
            f"volume={volume},"
            f"afade=t=in:st=0:d=0.01,"
            f"afade=t=out:st=0.03:d=0.09,"
            f"adelay={delay_ms}|{delay_ms}[s{i}]"
        )
        filter_parts.append(
            f"anoisesrc=color=brown:duration=0.15:sample_rate={SR},"
            f"volume={volume * 0.3},"
            f"highpass=f=500,"
            f"lowpass=f=2000,"
            f"afade=t=in:st=0:d=0.01,"
            f"afade=t=out:st=0.05:d=0.1,"
            f"adelay={delay_ms}|{delay_ms}[n{i}]"
        )
    n_inputs = n_steps * 2
    mix_inputs = "".join(f"[s{i}][n{i}]" for i in range(n_steps))
    filter_parts.append(f"{mix_inputs}amix=inputs={n_inputs}:duration=longest[out]")
    filter_complex = ";".join(filter_parts)
    total_dur = n_steps * interval + 0.2
    cmd = [FF, "-y", "-filter_complex", filter_complex,
           "-map", "[out]", "-t", str(total_dur), "-ac", "1", out_path]
    run(cmd)


make_footsteps(6, f"{SFX_DIR}/footsteps_slow.wav", interval=0.7, volume=0.2)
make_footsteps(12, f"{SFX_DIR}/footsteps_fast.wav", interval=0.35, volume=0.3)

# 8. 水洒地声
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"anoisesrc=color=pink:duration=0.8:sample_rate={SR},"
       f"volume=0.3,"
       f"lowpass=f=1500,"
       f"highpass=f=200,"
       f"afade=t=in:st=0:d=0.05,"
       f"afade=t=out:st=0.3:d=0.5",
       "-ac", "1", f"{SFX_DIR}/water_spill.wav"]
run(cmd)

# 9. 手机解锁/振动
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=1200:duration=0.15:sample_rate={SR},"
       f"volume=0.2,"
       f"afade=t=in:st=0:d=0.01,"
       f"afade=t=out:st=0.05:d=0.1",
       "-ac", "1", f"{SFX_DIR}/phone_unlock.wav"]
run(cmd)

cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=150:duration=0.5:sample_rate={SR},"
       f"volume=0.15,"
       f"tremolo=f=20:d=0.8,"
       f"afade=t=in:st=0:d=0.05,"
       f"afade=t=out:st=0.2:d=0.3",
       "-ac", "1", f"{SFX_DIR}/phone_vibrate.wav"]
run(cmd)

# 10. 拍门声
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=90:duration=0.3:sample_rate={SR},"
       f"volume=0.6,"
       f"afade=t=in:st=0:d=0.005,"
       f"afade=t=out:st=0.05:d=0.25,"
       f"lowpass=f=300",
       "-ac", "1", f"{SFX_DIR}/door_bang_single.wav"]
run(cmd)

# 连拍门（3下）
cmd = [FF, "-y", "-filter_complex",
       f"sine=frequency=90:duration=0.3:sample_rate={SR},volume=0.6,afade=t=in:st=0:d=0.005,afade=t=out:st=0.05:d=0.25,lowpass=f=300,adelay=0|0[b1];"
       f"sine=frequency=85:duration=0.3:sample_rate={SR},volume=0.55,afade=t=in:st=0:d=0.005,afade=t=out:st=0.05:d=0.25,lowpass=f=300,adelay=400|400[b2];"
       f"sine=frequency=95:duration=0.35:sample_rate={SR},volume=0.7,afade=t=in:st=0:d=0.005,afade=t=out:st=0.05:d=0.3,lowpass=f=300,adelay=800|800[b3];"
       "[b1][b2][b3]amix=inputs=3:duration=longest[out]",
       "-map", "[out]", "-t", "1.5", "-ac", "1",
       f"{SFX_DIR}/door_bang_3x.wav"]
run(cmd)

# 11. 门开吱呀
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=180:duration=2.0:sample_rate={SR},"
       f"volume=0.25,"
       f"tremolo=f=3:d=0.4,"
       f"afade=t=in:st=0:d=0.2,"
       f"afade=t=out:st=1.5:d=0.5,"
       f"lowpass=f=500",
       "-ac", "1", f"{SFX_DIR}/door_squeak.wav"]
run(cmd)

# 12. 耳鸣声
cmd = [FF, "-y", "-f", "lavfi", "-i",
       f"sine=frequency=4000:duration=1.0:sample_rate={SR},"
       f"volume=0.08,"
       f"afade=t=in:st=0:d=0.3,"
       f"afade=t=out:st=0.7:d=0.3",
       "-ac", "1", f"{SFX_DIR}/tinnitus_ring.wav"]
run(cmd)

print("所有音效合成完成")

# ============================================================
# 第二部分：合成 BGM（悬疑氛围垫）
# ============================================================
print("=== Part 2: 合成 BGM ===")

cmd = [FF, "-y", "-filter_complex",
       f"sine=frequency=45:duration=90:sample_rate={SR},volume=0.1,lowpass=f=100,tremolo=f=0.15:d=0.2[drone];"
       f"sine=frequency=67:duration=90:sample_rate={SR},volume=0.06,lowpass=f=150,tremolo=f=0.2:d=0.3[drone2];"
       f"anoisesrc=color=pink:duration=90:sample_rate={SR},volume=0.03,lowpass=f=2000,highpass=f=200,tremolo=f=0.1:d=0.4[texture];"
       f"sine=frequency=55:duration=90:sample_rate={SR},volume=0.05,tremolo=f=0.1:d=0.6[pulse];"
       "[drone][drone2][texture][pulse]amix=inputs=4:duration=first:normalize=0[bgm_raw];"
       "[bgm_raw]lowpass=f=800,highpass=f=20,acompressor=threshold=-20dB:ratio=4:attack=50:release=500[out]",
       "-map", "[out]", "-ac", "2", f"{SFX_DIR}/bgm_suspense_90s.wav"]
run(cmd)

print("BGM 合成完成")

# ============================================================
# 第三部分：配音时间线（带 J-cut 0.3s）
# ============================================================
print("=== Part 3: 配音时间线 ===")

VOICE_TIMELINE = [
    # S02 林晚"几点了" — J-cut: 黑屏最后0.3s进第一个字
    # 黑屏结束在 ~5.083s，第一个字出现在 ~4.8s（J-cut 0.3s）
    {"file": f"{VOICE_DIR}/S02_林晚_几点了.wav", "start": 4.8, "type": "normal", "vol": 1.0},

    # S03 林晚"302的光" — S03 开始 ~10.042s，J-cut 提前0.3s
    {"file": f"{VOICE_DIR}/S03_林晚_302的光.wav", "start": 9.7, "type": "normal", "vol": 1.0},

    # S04 林晚"谁" — S04 开始 ~12.050s，J-cut 提前0.3s
    {"file": f"{VOICE_DIR}/S04_林晚_谁.wav", "start": 11.75, "type": "normal", "vol": 1.0},

    # S05 影"谁" — S05 开始 ~15.658s，J-cut 提前0.3s，门内闷声
    {"file": f"{VOICE_DIR}/S05_影_谁.wav", "start": 15.35, "type": "behind_door", "vol": 0.9},

    # S10 林晚"你是谁" — S10 开始 ~51.967s，J-cut 提前0.3s
    {"file": f"{VOICE_DIR}/S10_林晚_你是谁.wav", "start": 51.67, "type": "normal", "vol": 1.0},

    # S10 影"你是谁"（延迟2s版本）— 回声效果
    # 林晚说"你是谁"约 51.67 + 1.38 ≈ 53.05s 说完，影延迟约2s
    {"file": f"{VOICE_DIR}/S10_影_你是谁_延迟2s.wav", "start": 53.7, "type": "echo", "vol": 0.65},

    # S11 林晚崩溃 — S11a 开始 ~59.975s，J-cut 提前0.3s
    {"file": f"{VOICE_DIR}/S11_林晚_崩溃.wav", "start": 59.68, "type": "shout", "vol": 1.15},
]

print(f"配音条目: {len(VOICE_TIMELINE)} 条")

# ============================================================
# 第四部分：音效时间线
# ============================================================
print("=== Part 4: 音效时间线 ===")

SFX_TIMELINE = [
    # --- 开场蒙太奇 ---
    # A1 0-1s: 低频嗡鸣渐入
    {"file": f"{SFX_DIR}/drone_40hz_10s.wav", "start": 0.0, "vol": 0.25, "dur": 4.5, "fade_in": 0.8, "fade_out": 0.3},
    # A2 1.0s: 低频冲击
    {"file": f"{SFX_DIR}/thump_low.wav", "start": 1.0, "vol": 0.5},
    # A3 1.5s: 嗒声（眼皮声）
    {"file": f"{SFX_DIR}/click_light.wav", "start": 1.5, "vol": 0.4},
    # A4-A5 2.0-4.5s: 心跳渐强 90BPM
    {"file": f"{SFX_DIR}/heartbeat_opening.wav", "start": 2.0, "vol": 0.6, "dur": 3.0, "fade_in": 0.3},
    # A5 4.0s: 心跳突然放大（重击）
    {"file": f"{SFX_DIR}/thump_heavy.wav", "start": 4.0, "vol": 0.45},
    # A6 4.7s: 心跳最后一下重击
    {"file": f"{SFX_DIR}/thump_low.wav", "start": 4.7, "vol": 0.55},
    # A6 5.3s: silence 后一声轻咔哒（门锁声）
    {"file": f"{SFX_DIR}/click_doorlock.wav", "start": 5.3, "vol": 0.5},

    # --- 全片环境嗡鸣（垫底）---
    {"file": f"{SFX_DIR}/ambient_drone_90s.wav", "start": 0.0, "vol": 0.2, "dur": TOTAL_DUR, "fade_in": 2.0, "fade_out": 3.0},

    # --- S02 段 ---
    # 脚步声（停步前几步）
    {"file": f"{SFX_DIR}/footsteps_slow.wav", "start": 5.1, "vol": 0.3, "dur": 3.0},
    # 呼吸声（紧张）
    {"file": f"{SFX_DIR}/breathing_15s.wav", "start": 7.5, "vol": 0.2, "dur": 3.5},

    # --- S04→S05 奇观1（白闪） ---
    {"file": f"{SFX_DIR}/whoosh_white.wav", "start": 15.55, "vol": 0.4},
    {"file": f"{SFX_DIR}/thump_low.wav", "start": 15.65, "vol": 0.5},

    # --- S06 眼睛特写 ---
    {"file": f"{SFX_DIR}/breathing_fast_3s.wav", "start": 26.0, "vol": 0.25, "dur": 3.0},

    # --- S07 后退洒水 ---
    {"file": f"{SFX_DIR}/footsteps_fast.wav", "start": 29.5, "vol": 0.35, "dur": 2.5},
    # 水洒地声（约 S07 第6s 处 = 28.98 + 6 = 34.98s）
    {"file": f"{SFX_DIR}/water_spill.wav", "start": 35.0, "vol": 0.4},

    # --- S08 手机微光 ---
    {"file": f"{SFX_DIR}/phone_unlock.wav", "start": 38.0, "vol": 0.3},
    {"file": f"{SFX_DIR}/phone_vibrate.wav", "start": 39.5, "vol": 0.25},

    # --- S08→S09 奇观2（黑闪） ---
    {"file": f"{SFX_DIR}/whoosh_low.wav", "start": 41.9, "vol": 0.45},
    {"file": f"{SFX_DIR}/thump_heavy.wav", "start": 42.0, "vol": 0.45},
    # 耳鸣声（对掌瞬间，约 S09 最后）
    {"file": f"{SFX_DIR}/tinnitus_ring.wav", "start": 51.5, "vol": 0.3},

    # --- S11 拍门 ---
    {"file": f"{SFX_DIR}/door_bang_3x.wav", "start": 60.5, "vol": 0.6},
    # 急促呼吸
    {"file": f"{SFX_DIR}/breathing_fast_3s.wav", "start": 60.0, "vol": 0.35, "dur": 3.5},

    # --- S12 门开 ---
    {"file": f"{SFX_DIR}/door_squeak.wav", "start": 63.7, "vol": 0.35, "dur": 2.0, "fade_in": 0.2},

    # --- S12→S13 奇观3（黑闪） ---
    {"file": f"{SFX_DIR}/whoosh_low.wav", "start": 67.4, "vol": 0.45},
    {"file": f"{SFX_DIR}/thump_low.wav", "start": 67.5, "vol": 0.5},
    # 对峙呼吸声
    {"file": f"{SFX_DIR}/breathing_15s.wav", "start": 67.6, "vol": 0.3, "dur": 4.0},

    # --- S14 转身跑 ---
    {"file": f"{SFX_DIR}/footsteps_fast.wav", "start": 71.3, "vol": 0.4, "dur": 2.0},

    # --- S15 结尾 ---
    {"file": f"{SFX_DIR}/breathing_fast_3s.wav", "start": 73.0, "vol": 0.3, "dur": 3.0},
    # 心跳声（发现异常时）
    {"file": f"{SFX_DIR}/heartbeat_fast.wav", "start": 74.0, "vol": 0.5, "dur": 3.0},
    # 定格重击
    {"file": f"{SFX_DIR}/thump_heavy.wav", "start": 77.1, "vol": 0.6},
    # 耳鸣（定格后）
    {"file": f"{SFX_DIR}/tinnitus_ring.wav", "start": 77.3, "vol": 0.4},
]

print(f"音效条目: {len(SFX_TIMELINE)} 条")

# ============================================================
# 第五部分：BGM 分段起伏
# ============================================================
print("=== Part 5: BGM 时间线 ===")

BGM_SEGMENTS = [
    # 开场蒙太奇：渐入
    {"start": 0.0, "end": 5.1, "vol": 0.35, "fade_in": 1.0, "fade_out": 0.5},
    # 开场叙事 S02-S04：低音量
    {"start": 5.1, "end": 15.6, "vol": 0.25},
    # 第一奇观 S05：推高
    {"start": 15.6, "end": 25.5, "vol": 0.4},
    # S06-S07：维持
    {"start": 25.5, "end": 37.0, "vol": 0.35},
    # S08 探索：降低
    {"start": 37.0, "end": 42.0, "vol": 0.25},
    # 第二奇观 S09：推高
    {"start": 42.0, "end": 52.0, "vol": 0.45},
    # S10 回声：降低（突出人声）
    {"start": 52.0, "end": 60.0, "vol": 0.2},
    # S11-S13 高潮：推到最高
    {"start": 60.0, "end": 71.2, "vol": 0.5},
    # S14-S15a：渐弱
    {"start": 71.2, "end": 77.1, "vol": 0.3, "fade_out": 2.0},
    # 定格后：极弱
    {"start": 77.1, "end": TOTAL_DUR, "vol": 0.05, "fade_out": 1.5},
]

print(f"BGM 分段: {len(BGM_SEGMENTS)} 段")

# ============================================================
# 第六部分：混音（分层生成 WAV 再总混）
# 使用 -i 输入方式，避免 amovie 路径转义问题
# ============================================================
print("=== Part 6: 最终混音 ===")


def build_mix_layer(items, out_path, label="layer"):
    """通用：将一组带时间码的音频文件混合成一层 WAV（用 -i 输入方式）"""
    print(f"  混合{label}层... ({len(items)} 个元素)")
    n = len(items)

    # 构建 ffmpeg 命令：多个 -i 输入
    cmd = [FF, "-y"]
    for item in items:
        cmd += ["-i", item["file"]]

    # 构建 filter_complex
    parts = []
    for i, item in enumerate(items):
        delay_ms = int(item["start"] * 1000)
        vol = item.get("vol", 1.0)
        dur = item.get("dur", None)
        extra_af = item.get("af", "")

        afilters = []
        if extra_af:
            afilters.append(extra_af)
        afilters.append(f"volume={vol}")
        if dur:
            afilters.append(f"atrim=0:{dur}")
        if item.get("fade_in", 0) > 0:
            afilters.append(f"afade=t=in:st=0:d={item['fade_in']}")
        if item.get("fade_out", 0) > 0:
            actual_dur = dur if dur else 2.0
            fo_start = max(0.001, actual_dur - item["fade_out"])
            afilters.append(f"afade=t=out:st={fo_start}:d={item['fade_out']}")

        af_str = ",".join(afilters) if afilters else "anull"
        parts.append(f"[{i}:a]{af_str},adelay={delay_ms}|{delay_ms}[l{i}]")

    inputs_str = "".join(f"[l{i}]" for i in range(n))
    parts.append(f"{inputs_str}amix=inputs={n}:duration=longest:normalize=0,"
                 f"apad=whole_dur={TOTAL_DUR}[out]")

    filter_complex = ";".join(parts)
    cmd += ["-filter_complex", filter_complex,
            "-map", "[out]", "-ac", "2", "-ar", str(SR), out_path]
    run(cmd)


# --- 层1：配音 ---
voice_items = []
for v in VOICE_TIMELINE:
    extra_af = ""
    if v["type"] == "behind_door":
        extra_af = "lowpass=f=1500,aecho=0.6:0.3:100:0.3"
    elif v["type"] == "echo":
        extra_af = "lowpass=f=2000,aecho=0.7:0.5:200:0.3"
    elif v["type"] == "shout":
        extra_af = ("highpass=f=200,"
                    "acompressor=threshold=-15dB:ratio=8:attack=5:release=100,"
                    "alimiter=limit=-1.5dB")
    voice_items.append({
        "file": v["file"],
        "start": v["start"],
        "vol": v["vol"],
        "af": extra_af,
    })

build_mix_layer(voice_items, f"{TMP}/voices_layer.wav", "配音")

# --- 层2：音效 ---
build_mix_layer(SFX_TIMELINE, f"{TMP}/sfx_layer.wav", "音效")

# --- 层3：BGM ---
bgm_path = f"{SFX_DIR}/bgm_suspense_90s.wav"
bgm_items = []
for seg in BGM_SEGMENTS:
    item = {
        "file": bgm_path,
        "start": seg["start"],
        "vol": seg["vol"],
        "dur": seg["end"] - seg["start"],
    }
    if seg.get("fade_in"):
        item["fade_in"] = seg["fade_in"]
    if seg.get("fade_out"):
        item["fade_out"] = seg["fade_out"]
    bgm_items.append(item)

build_mix_layer(bgm_items, f"{TMP}/bgm_layer.wav", "BGM")

# --- 三层总混 ---
print("  三层总混 + 母带处理...")
cmd = [FF, "-y",
       "-i", f"{TMP}/voices_layer.wav",
       "-i", f"{TMP}/sfx_layer.wav",
       "-i", f"{TMP}/bgm_layer.wav",
       "-filter_complex",
       "[0:a]volume=1.0[v];"
       "[1:a]volume=0.9[s];"
       "[2:a]volume=0.6[b];"
       "[v][s][b]amix=inputs=3:duration=first:normalize=0,"
       "acompressor=threshold=-18dB:ratio=3:attack=10:release=200,"
       "alimiter=limit=-1.5dB,"
       "loudnorm=I=-18:TP=-1.5:LRA=11[final]",
       "-map", "[final]",
       "-ac", "2", "-ar", str(SR),
       FINAL_AUDIO]
run(cmd)

print(f"音轨输出: {FINAL_AUDIO}")

# ============================================================
# 第七部分：合并视频 + 音频
# ============================================================
print("=== Part 7: 合并视频+音频 ===")
cmd = [FF, "-y",
       "-i", VIDEO_FILE,
       "-i", FINAL_AUDIO,
       "-c:v", "copy",
       "-c:a", "aac", "-b:a", "192k",
       "-shortest",
       FINAL_VIDEO]
run(cmd)

actual_dur = get_dur(FINAL_VIDEO)
print(f"\n=== 完成 ===")
print(f"最终成片: {FINAL_VIDEO}")
print(f"总时长: {actual_dur:.3f} 秒")
