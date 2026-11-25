# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, r"C:/Users/admin/AppData/Local/hermes/skills/creative/ai-comic-drama-pipeline/scripts")
import muse_qc
f = r"D:/Hermes环境准备/AI漫剧制作/04_视频素材/待生成/ep01/EP01_S1_frames/f1.png"
exp = [{"text":"画面主体是深夜楼道","kind":"must","cat":"空间"},
       {"text":"画面中不出现字幕水印","kind":"must_not","cat":"文字"}]
t=time.time()
try:
    r = muse_qc.ask_vision(f, exp)
    print("ASK_VISION_OK", round(time.time()-t,1),"秒", r)
except Exception as e:
    print("ASK_VISION_FAIL", round(time.time()-t,1),"秒", type(e).__name__, str(e)[:200])
