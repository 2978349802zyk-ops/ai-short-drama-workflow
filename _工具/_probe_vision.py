
import base64,json,time,urllib.request
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def ask(f,label):
    b=open(f,"rb").read(); b64=base64.b64encode(b).decode()
    payload={"model":"group/free","max_tokens":200,"messages":[{"role":"user","content":[
      {"type":"text","text":"这张图里有几扇门？只回答数字。"},
      {"type":"image_url","image_url":{"url":"data:image/png;base64,"+b64}}]}]}
    req=urllib.request.Request("http://127.0.0.1:3425/v1/chat/completions",data=json.dumps(payload).encode(),
      headers={"Content-Type":"application/json","x-api-key":"sk-local"})
    t=time.time()
    try:
        r=json.load(OPENER.open(req,timeout=90))
        print(label,"%.1fs"%(time.time()-t),"|",len(b),"B | ans:",r["choices"][0]["message"].get("content","")[:40])
    except Exception as e:
        print(label,"ERR %.1fs"%(time.time()-t),str(e)[:70])
ask("D:/Hermes环境准备/AI漫剧制作/新剧_回声公寓_达标版/视频素材/EP01_P01_S1_frames/f1.png","原图")
ask("D:/Hermes环境准备/AI漫剧制作/_f1_small.png","缩图")
