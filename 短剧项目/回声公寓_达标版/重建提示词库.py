#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""只重建 提示词库_带参考图.json（修 brief 用）：不动剧本正文/台词/自检/审查报告。"""
import json, os, sys
sys.path.insert(0, "C:/Users/admin/AppData/Local/hermes/skills/creative/ai-comic-drama-pipeline/scripts")
import drama_from_theme as D

OUT = "D:/Hermes环境准备/AI漫剧制作/新剧_回声公寓_达标版"
REF = os.path.join(OUT, "定妆图")
obj = json.load(open(f"{OUT}/剧本.json", encoding="utf-8"))

lib = []
for s in obj["shots"]:
    role = s.get("ref_role", "")
    ref_path = os.path.join(REF, role + ".png") if role else ""
    brief = D.build_brief(s, "")
    lib.append({
        "shot_id": s["shot_id"], "brief": brief,
        "scene": s.get("场景信息", ""), "duration": s.get("建议时长", 5),
        "mood": s.get("人物动作", ""),
        "ref": [ref_path] if ref_path else [], "ref_role": role,
    })
    print(s["shot_id"], "| 未定妆标记:", brief.count("草稿·角色未定妆"), "| 长度:", len(brief))

json.dump(lib, open(f"{OUT}/提示词库_带参考图.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\n提示词库已重建（%d 镜）" % len(lib))
print("\nS1 brief 示例:\n", lib[0]["brief"])
