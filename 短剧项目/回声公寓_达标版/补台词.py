#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
给已达标《回声公寓》剧本补台词（不调 LLM、不重新创作）。
依据每镜已有的剧情目的/动作/表情/声音设计填 dialogue + 台词表 + 字幕建议，
然后调用 drama_from_theme 的 validate()/write_outputs() 重跑自检并重新落盘全部产物。
"""
import json, os, sys
sys.path.insert(0, "C:/Users/admin/AppData/Local/hermes/skills/creative/ai-comic-drama-pipeline/scripts")
import drama_from_theme as D

OUT = "D:/Hermes环境准备/AI漫剧制作/新剧_回声公寓_达标版"

# 依已有剧情补的台词。设计：S5「影」以与林晚完全相同的声音复述 S4 的问话，
# 呼应剧名"回声"与 S6 声音设计里"一模一样的呼吸声"。
DIALOG = {
    "EP01_P01_S2": ("林晚", "……几点了，怎么一点声音都没有。"),
    "EP01_P01_S3": ("林晚", "……302，这光是从门缝里透出来的？"),
    "EP01_P01_S4": ("林晚", "……谁？"),
    "EP01_P01_S5": ("影",   "……谁？"),   # 与林晚同句、同音色——回声点
    # S1 空镜无人物、S6 开放式结尾留白：保持无台词，只用声音设计收尾
}

obj = json.load(open(f"{OUT}/剧本.json", encoding="utf-8"))
for s in obj["shots"]:
    sid = s["shot_id"]
    if sid in DIALOG:
        role, line = DIALOG[sid]
        s["dialogue"] = line
        s["字幕建议"] = line                      # 字幕建议同步为台词，供剪辑层烧字幕
        if sid == "EP01_P01_S5":
            s["声音设计"] = ("极度安静；影开口时声音与林晚完全一致（同一音色、同一语气），"
                          "制造「另一个自己」的回声感；其余仅极轻呼吸声，与门外呼吸频率错位。")
    else:
        s["dialogue"] = "无"

obj["台词表"] = [
    {"镜号": sid, "角色": role, "台词": line}
    for sid, (role, line) in DIALOG.items()
]

# 重跑代码层达标自检
fails, warns, stats = D.validate(obj, 6, "")
for w in warns:
    print("[警告]", w)
if fails:
    print("[FAIL] 自检未过，拒绝落盘：")
    for f in fails:
        print("  -", f)
    sys.exit(2)
print("自检 FAIL=0 ✅（固定镜 %d/%d，时长 %.1f 秒，台词 %d 条）" %
      (stats["fixed"], stats["shots"], stats["total_dur"], len(obj["台词表"])))

# 重新落盘全部产物
D.write_outputs(obj, OUT, os.path.join(OUT, "定妆图"), "", stats)
print("已重新落盘：剧本.json / 分镜表_25列.csv / 提示词库 / 定妆图提示词 / 连续性矩阵 / 自检报告")
print("台词表：")
for t in obj["台词表"]:
    print("  %s  %s：%s" % (t["镜号"], t["角色"], t["台词"]))
