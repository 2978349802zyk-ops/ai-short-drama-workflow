# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, r"C:/Users/admin/AppData/Local/hermes/skills/creative/ai-comic-drama-pipeline/scripts")
import muse_prompt
b = {"shot_id": "EP01_P01_S1", "brief": "无。画面保持静止，仅有门缝暖光轻微明暗晃动，固定镜头拍摄。", "scene": "老旧公寓3楼楼道，墙面斑驳掉皮，贴着泛黄的小广告，水泥地面磨花，感应灯故障熄灭，走廊尽头的绿色安全出口指示灯微弱发亮，302号棕红色旧木门位于楼道中段，门缝透出极细的暖光", "kind": "video", "duration": 10, "out": "D:/Hermes环境准备/AI漫剧制作/第一集完整剧情/视频素材/EP01_P01_S1.mp4", "ref": ["D:/Hermes环境准备/AI漫剧制作/03_角色与场景素材/场景\\S01_夜楼道.png"]}
built = muse_prompt.build(b["brief"], 10, b["scene"], use_llm=False)
for e in built["expectations"]:
    print(e["kind"], "|", e["cat"], "|", e["text"])
