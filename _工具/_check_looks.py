import sys;sys.path.insert(0,"C:/Users/admin/AppData/Local/hermes/skills/creative/ai-comic-drama-pipeline/scripts")
import gen_looks
items=gen_looks.parse_looks("D:/Hermes环境准备/AI漫剧制作/新剧_回声公寓_达标版/角色定妆图提示词.txt")
print("角色数:",len(items))
for n,p in items:
    print(n,"| 含未定妆声明:", "未定妆" in p, "| prompt头:", p[:50])
