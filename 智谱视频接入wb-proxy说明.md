# 智谱 CogVideoX 接入 wb-proxy（2026-11-22）

## 一句话结论

`http://127.0.0.1:8788/v1/videos` 现在一个口子管两条路：**模型名带 `cogvideox` 的走智谱免费档**，其它模型照旧走 workbuddy。调用方不用改代码，只换模型名。

## 怎么用（拿来即用）

```bash
# 提交（竖屏短剧规格，免费档 0 元）
curl --noproxy '*' -X POST http://127.0.0.1:8788/v1/videos \
  -H "Authorization: Bearer <wb-proxy 的 key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"cogvideox-flash","prompt":"夜色中的旧公寓楼道，声控灯忽明忽暗，镜头缓慢前推，写实电影质感","size":"1080x1920","seconds":5,"fps":30}'

# 查状态（返回里的 id 自带 zp_ 前缀，直接塞回来）
curl --noproxy '*' http://127.0.0.1:8788/v1/videos/zp_<智谱任务id> \
  -H "Authorization: Bearer <wb-proxy 的 key>"

# 拿片子（完成后再调，直接吐 MP4 字节流）
curl --noproxy '*' -o out.mp4 http://127.0.0.1:8788/v1/videos/zp_<智谱任务id>/content \
  -H "Authorization: Bearer <wb-proxy 的 key>"
```

## 模型名对照

| 你写的模型名 | 实际走哪 | 花钱 |
|---|---|---|
| `cogvideox-flash` / `zhipu-flash` / `cogvideox` | 智谱 CogVideoX-Flash | 0 元 |
| `cogvideox-3` / `zhipu-3` | 智谱 CogVideoX-3 | 约 1 元/次（特惠约 0.3 元） |
| 其它任何名字（kling / veo / sora …） | workbuddy 老链路 | 按 workbuddy 计费 |

## 请求字段

- `prompt` 必填，空会直接 400，不会打到上游。
- `size` 只认智谱枚举：`720x480 / 1024x1024 / 1280x960 / 960x1280 / 1920x1080 / 1080x1920 / 2048x1080 / 3840x2160`。
  给别的尺寸（比如 `720x1280`）会按长短边比例就近映射，**竖图不会变成横图**。
- 不写 `size` 就给 `1080x1920`（漫剧竖屏）。
- `seconds` 只支持 5 或 10，写 8 会被归到 10。
- `fps` 只支持 30 或 60。
- `negative_prompt` 智谱没有独立字段，会被拼成「避免出现：…」接在正文后面。
- `enable_audio` / `with_audio` 传 true 才带音效。
- 首帧：`input_reference` 优先，其次 `image_url`。Flash 只吃**一张图**，传两张会 400 并提示改用 `cogvideox-3`。

## 已验证的路由行为

| 探测 | 结果 | 说明 |
|---|---|---|
| 空 prompt | 400 `missing required field: prompt` | 本地拦截，不打上游 |
| `GET /v1/videos/zp_0000000000000000` | 404 `任务：0000000000000000不存在。` | 确实查的智谱 async-result |
| 正常提交（窗口关闭时） | 429 `该模型当前访问量过大` | 限流原样透传，调用方自己退避 |

**真实成功链路（2026-11-23 实测，不耗新额度）**：拿直连已成功的任务号加 `zp_` 前缀，经 8788 查询（`GET /v1/videos/zp_…`）返回 `status=completed`，再经 `GET /v1/videos/zp_…/content` 下载到 MP4；两份文件与直连产物的 SHA256 完全一致。

**没实测到的只剩一步**：经 8788「提交」并等到完成——原因是免费窗口时开时关，反复 429；提交逻辑与直连共用同一智谱接口，且 400/429 已证明请求确实打到了智谱。

## 改了什么文件

- 新增 `D:\反代\wb-proxy\wb_zhipu_video.py`（377 行）：提交/查询/下载 + 尺寸与模型名归一化，自带 `__main__` 自检（不联网）。
- 改 `wb_proxy.py` 三处：`_handle_videos_create` 顶部按模型名分流；`_handle_video_status` / `_handle_video_content` 按 `zp_` 前缀分流。备份在 `wb_proxy.py.bak-20261122-224242`。

## 运维注意

- 本机有守夜进程 `D:\Hermes环境准备\...\watchdog.py` 会盯着 wb-proxy，**杀掉会自动重启**（重启后加载新代码，不用手动起）。
- 8788 的鉴权 key 只在启动命令行里（面板密钥 0 条）。要读它就去进程命令行里取，别打印出来。
- 智谱 key 存在 `D:\ai漫剧\.zhipu_key`，也可用环境变量 `ZHIPU_API_KEY` 覆盖。
- 免费档 429 是常态，重试退避要按 20→40→80→160→320→600 秒爬。

## 画质相关的现实约束

- 免费档竖屏**最高只有 1080x1920**，没有 4K 竖屏（4K 只有 3840x2160 横屏）。
- 之前 720x480 的片子画质差是因为尺寸太小；短剧必须用 1080x1920。
- 图生视频时首帧里**必须有人**，否则模型会自己编一个角色，还会把写实画风拐成 2D。
