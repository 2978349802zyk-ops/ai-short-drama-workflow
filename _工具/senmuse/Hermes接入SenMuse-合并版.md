# Hermes 接入 SenMuse（合并版：提示词 + 调用模块 + 多账号池）

> 给 Hermes 的完整任务说明。把本文件发给 Hermes，它按下面执行即可。
> 前提：SenMuse 服务已在本机运行（`node scripts/senmuse-api.mjs serve --data .senmuse-api`），
> doctor 已通过，令牌只从环境变量读（不要写进代码、不要进仓库）。
> 出片脚本已定位：`D:\Hermes环境准备\muse-video-station\upstream\muse2api\engine.py` 的 `MuseEngine.generate()`，不要新建 muse_shoot.py。

---

## 一、任务：把 SenMuse 接进 engine.py

把第二节 `senmuse_client.py` 和第三节 `senmuse_pool.py` 存成文件（与 engine.py 同目录或其可 import 的位置），然后改 `MuseEngine.generate()`：

1. 先读 `generate()` 的签名、返回结构、错误处理，以及 app.py / worker.js 怎么消费结果，把接口契约报给用户确认，先不要改
2. 在 `generate()` 内部加 SenMuse 后端：用 `SenMusePool.generate()`（4 实例轮换，配置见 instances.example.json），保持原有签名和返回结构不变，上层无感
3. 后端可切换：默认 SenMuse；只有 SenMuse 在提交前就失败（实例全不可用）时才回退 CDP；已提交状态不确定时不许换后端重交，抛错等人工处理
4. `request_id` 用 `make_request_id(项目slug, 集, 镜号, attempt)`；台账（generation_ledger.json）防重复：同一 request_id 完成过就直接返回已有文件，失败不自动换账号重交
5. 参考图最多 6 张全喂（头身分拆包正好 6 张）；aspect 固定 9:16；连续镜头可用 kind=extend + conversation_id 续拍
6. 原有硬规矩（一次一镜、生成后验收、内容去重、失败最多重生 1 次且换条件、连续 2 镜失败停批）保持在工作流层不动
7. 令牌只从环境变量读；实例清单可以进仓库，台账和令牌不进

改完报行号和接口契约对照，不要跑生产。

---

## 二、senmuse_client.py（完整源码，保存为同名文件）

```python
"""SenMuse REST 客户端（给 Hermes 用，仅标准库，无第三方依赖）。

用法示例：
    from senmuse_client import SenMuseClient, make_request_id

    client = SenMuseClient()  # token 从环境变量 SENMUSE_API_TOKEN 读
    result = client.generate(
        request_id=make_request_id("回声公寓", "EP02", "S03", attempt=1),
        kind="video",
        prompt="……",
        reference_paths=[r"D:\\...\\head_front.png", r"D:\\...\\body_front.png"],
        aspect="9:16",
        out_dir=r"D:\\Hermes环境准备\\AI漫剧制作\\短剧项目\\回声公寓\\EP02\\shots",
    )
    # result: {"job": {...}, "files": [本地文件路径, ...]}

纪律（与现有工作流硬规矩对齐）：
- request_id 必须稳定：同一镜重试复用同一个 id，服务端幂等，不会重复生成扣额度。
- 任务进入 failed / needs_review / cancelled 时本模块抛 SenMuseError 并附带 job 全文，
  绝不自动重交——先查清原任务状态再决定（见 docs/MUSE_API.md 的保守记录原则）。
- 一次只跑一镜：服务端同一账号同时只允许一个生成任务，批量调用请串行。
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE = "http://127.0.0.1:47831"
TERMINAL_OK = {"completed"}
TERMINAL_BAD = {"failed", "needs_review", "cancelled"}


class SenMuseError(RuntimeError):
    def __init__(self, message: str, job: dict | None = None):
        super().__init__(message)
        self.job = job


def make_request_id(project: str, episode: str, shot: str, attempt: int = 1) -> str:
    """生成 8–100 字符的稳定 ASCII requestId，如 'huisheng-EP02-S03-a1'。

    project 建议传拼音/英文 slug（中文会被过滤）；同一镜重试传相同 attempt，
    确认要重新生成时 attempt+1。
    """
    raw = f"{project}-{episode}-{shot}-a{attempt}"
    slug = re.sub(r"[^A-Za-z0-9_-]", "-", raw).strip("-")
    if len(slug) < 8:
        slug = (slug + "-senmuse")[:100]
    return slug[:100]


class SenMuseClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE,
        token: str | None = None,
        token_file: str | os.PathLike | None = None,
        timeout: float = 60.0,
    ):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        if token is None:
            token = os.environ.get("SENMUSE_API_TOKEN")
        if token is None and token_file is not None:
            token = Path(token_file).read_text(encoding="utf-8").strip()
        if not token:
            raise SenMuseError(
                "缺少 API 令牌：请设置环境变量 SENMUSE_API_TOKEN，"
                "或传 token_file 指向 .senmuse-api/api-token"
            )
        self._token = token

    # ---------- 底层请求 ----------
    def _request(self, method: str, path: str, *, json_body=None, raw=None, headers=None):
        url = self.base + path
        data = raw
        hdrs = {"Authorization": f"Bearer {self._token}"}
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
                ctype = resp.headers.get_content_type()
                if ctype == "application/json" and body:
                    return json.loads(body.decode("utf-8"))
                return body
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            raise SenMuseError(f"HTTP {e.code} {method} {path}: {detail}") from e
        except urllib.error.URLError as e:
            raise SenMuseError(f"连不上 SenMuse 服务（{self.base}）：{e.reason}") from e

    # ---------- 基础接口 ----------
    def health(self) -> bool:
        try:
            data = self._request("GET", "/healthz")
            return bool(isinstance(data, dict) and data.get("alive"))
        except SenMuseError:
            return False

    def status(self) -> dict:
        return self._request("GET", "/v1/status")

    def upload_asset(self, path: str | os.PathLike) -> str:
        """上传一个参考素材，返回 asset id。"""
        p = Path(path)
        if not p.is_file():
            raise SenMuseError(f"参考素材不存在：{p}")
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        data = self._request(
            "POST",
            "/v1/assets",
            raw=p.read_bytes(),
            headers={"X-Filename": p.name, "Content-Type": mime},
        )
        return data["id"]

    def submit(
        self,
        *,
        request_id: str,
        kind: str,
        prompt: str,
        reference_ids: list[str] | None = None,
        aspect: str | None = None,
        duration: float | None = None,
        conversation_id: str | None = None,
    ) -> dict:
        """提交生成任务。kind: video / image / edit / extend。

        extend（续拍）必须传原任务的 conversation_id（或 reference_ids）。
        duration 只是提示词里的目标时长，实际时长由 Muse 决定。
        """
        body = {
            "requestId": request_id,
            "kind": kind,
            "prompt": prompt,
            "referenceIds": reference_ids or [],
        }
        if aspect:
            body["aspect"] = aspect
        if duration is not None:
            body["duration"] = duration
        if conversation_id:
            body["conversationId"] = conversation_id
        return self._request("POST", "/v1/jobs", json_body=body)

    def get_job(self, job_id: str) -> dict:
        return self._request("GET", f"/v1/jobs/{job_id}")

    def wait(self, job_id: str, *, timeout: float = 1800.0, interval: float = 10.0) -> dict:
        """轮询到终态。completed 返回 job；failed/needs_review/cancelled 抛 SenMuseError（附 job）。"""
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            last = self.get_job(job_id)
            state = last.get("status")
            if state in TERMINAL_OK:
                return last
            if state in TERMINAL_BAD:
                raise SenMuseError(f"任务 {job_id} 状态 {state}，未自动重交，请先核查原任务", job=last)
            time.sleep(interval)
        raise SenMuseError(f"等待任务 {job_id} 超过 {timeout:.0f} 秒，最后状态：{last}", job=last)

    def download(self, asset_id: str, dest: str | os.PathLike) -> Path:
        """下载素材到 dest（先写 .part 再改名，避免半截文件被当成成品）。"""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = self._request("GET", f"/v1/assets/{asset_id}/file")
        if not isinstance(data, (bytes, bytearray)) or not data:
            raise SenMuseError(f"素材 {asset_id} 下载为空")
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(dest)
        return dest

    # ---------- 一站式 ----------
    def generate(
        self,
        *,
        request_id: str,
        kind: str,
        prompt: str,
        reference_paths: list[str | os.PathLike] | None = None,
        aspect: str | None = None,
        duration: float | None = None,
        conversation_id: str | None = None,
        out_dir: str | os.PathLike,
        name_prefix: str | None = None,
        wait_timeout: float = 1800.0,
    ) -> dict:
        """上传参考图 → 提交 → 等待 → 下载全部结果。返回 {"job":..., "files":[...]}。"""
        ref_ids = [self.upload_asset(p) for p in (reference_paths or [])]
        job = self.submit(
            request_id=request_id,
            kind=kind,
            prompt=prompt,
            reference_ids=ref_ids,
            aspect=aspect,
            duration=duration,
            conversation_id=conversation_id,
        )
        job = self.wait(job["id"], timeout=wait_timeout)
        out = Path(out_dir)
        files = []
        for i, asset_id in enumerate(job.get("assetIds") or []):
            ext = ".mp4" if kind in ("video", "edit", "extend") else ".png"
            stem = name_prefix or request_id
            dest = out / f"{stem}_{i + 1}{ext}" if len(job["assetIds"]) > 1 else out / f"{stem}{ext}"
            files.append(str(self.download(asset_id, dest)))
        if not files:
            raise SenMuseError("任务完成但没有返回素材", job=job)
        return {"job": job, "files": files}


def verify_media(path: str | os.PathLike) -> dict | None:
    """有 ffprobe 时核验媒体文件（时长/分辨率/编码）；没有则返回 None。"""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    out = subprocess.run(
        [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration,size",
            "-show_entries", "stream=codec_name,width,height",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        raise SenMuseError(f"ffprobe 核验失败：{path} {out.stderr[:300]}")
    return json.loads(out.stdout)
```

---

## 三、senmuse_pool.py（完整源码，保存为同名文件）

```python
"""SenMuse 多账号实例池（给 Hermes 用）：轮换派活 + 跨实例防重复生成。

核心纪律：
- 每个 Muse 账号一个 SenMuse 实例（独立 data 目录、端口、令牌）。
- 防重复靠本模块的台账（ledger JSON），不靠单实例的 requestId 幂等：
  同一 request_id 只要在任一实例上完成过，后续调用直接返回已有文件，不再生成。
- 已提交未完成的任务只轮询原实例，不换实例重交；失败不自动重试，
  要重生必须由调用方换 attempt（新 request_id）。
- 串行轮换：每镜选下一个 ready 的实例，不并行。

配置示例见 instances.example.json。令牌只从环境变量读，不进配置文件、不进仓库。
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from senmuse_client import SenMuseClient, SenMuseError


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class SenMusePool:
    def __init__(self, config_path: str | os.PathLike, ledger_path: str | os.PathLike):
        cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.instances: list[dict] = cfg["instances"]
        if not self.instances:
            raise SenMuseError("实例清单为空")
        self.ledger_path = Path(ledger_path)
        self._clients: dict[str, SenMuseClient] = {}
        self._ledger = self._load_ledger()

    # ---------- 台账 ----------
    def _load_ledger(self) -> dict:
        if self.ledger_path.is_file():
            return json.loads(self.ledger_path.read_text(encoding="utf-8"))
        return {"meta": {"next_index": 0}, "jobs": {}}

    def _save_ledger(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ledger_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.ledger_path)

    # ---------- 实例 ----------
    def _client(self, inst: dict) -> SenMuseClient:
        name = inst["name"]
        if name not in self._clients:
            token = os.environ.get(inst["token_env"])
            if not token:
                raise SenMuseError(f"实例 {name} 缺少令牌环境变量 {inst['token_env']}")
            self._clients[name] = SenMuseClient(base_url=inst["base_url"], token=token)
        return self._clients[name]

    def _pick_instance(self) -> dict:
        """轮询选下一个 ready 的实例；都不可用则抛错。"""
        n = len(self.instances)
        start = self._ledger["meta"].get("next_index", 0) % n
        errors = []
        for i in range(n):
            inst = self.instances[(start + i) % n]
            try:
                st = self._client(inst).status()
                if st.get("muse", {}).get("state") == "ready":
                    self._ledger["meta"]["next_index"] = (start + i + 1) % n
                    self._save_ledger()
                    return inst
                errors.append(f"{inst['name']}: state={st.get('muse', {}).get('state')}")
            except SenMuseError as e:
                errors.append(f"{inst['name']}: {e}")
        raise SenMuseError("没有可用的 SenMuse 实例：" + "；".join(errors))

    # ---------- 生成（带防重复） ----------
    def generate(
        self,
        *,
        request_id: str,
        kind: str,
        prompt: str,
        reference_paths: list | None = None,
        aspect: str | None = None,
        duration: float | None = None,
        conversation_id: str | None = None,
        out_dir: str | os.PathLike,
        name_prefix: str | None = None,
        wait_timeout: float = 1800.0,
    ) -> dict:
        jobs = self._ledger["jobs"]
        entry = jobs.get(request_id)

        # 1) 已完成且文件还在 → 直接返回，绝不重复生成
        if entry and entry.get("status") == "completed":
            files = [f for f in entry.get("files", []) if Path(f).is_file()]
            if files:
                return {"job": entry, "files": files, "cached": True, "instance": entry["instance"]}

        # 2) 已提交未完成 → 只轮询原实例
        if entry and entry.get("status") in ("queued", "running", "submitted"):
            inst = next(i for i in self.instances if i["name"] == entry["instance"])
            client = self._client(inst)
            job = client.wait(entry["job_id"], timeout=wait_timeout)
            return self._finish(request_id, inst, client, job, out_dir, name_prefix)

        # 3) 失败过 → 不自动重试，要求调用方换 attempt
        if entry and entry.get("status") in ("failed", "needs_review", "cancelled"):
            raise SenMuseError(
                f"{request_id} 之前已失败（{entry['status']}），不自动重交；"
                "确认要重生请换 attempt 生成新 request_id",
                job=entry,
            )

        # 4) 新任务 → 选实例提交，先记台账再等结果
        inst = self._pick_instance()
        client = self._client(inst)
        ref_ids = [client.upload_asset(p) for p in (reference_paths or [])]
        job = client.submit(
            request_id=request_id, kind=kind, prompt=prompt,
            reference_ids=ref_ids, aspect=aspect, duration=duration,
            conversation_id=conversation_id,
        )
        jobs[request_id] = {
            "instance": inst["name"], "job_id": job["id"], "status": job.get("status", "submitted"),
            "kind": kind, "files": [], "md5": [], "updated_at": time.time(),
        }
        self._save_ledger()
        job = client.wait(job["id"], timeout=wait_timeout)
        return self._finish(request_id, inst, client, job, out_dir, name_prefix)

    def _finish(self, request_id, inst, client, job, out_dir, name_prefix) -> dict:
        out = Path(out_dir)
        files, md5s = [], []
        asset_ids = job.get("assetIds") or []
        for i, asset_id in enumerate(asset_ids):
            ext = ".mp4" if job.get("kind") in ("video", "edit", "extend") else ".png"
            stem = name_prefix or request_id
            dest = out / (f"{stem}_{i + 1}{ext}" if len(asset_ids) > 1 else f"{stem}{ext}")
            client.download(asset_id, dest)
            files.append(str(dest))
            md5s.append(_md5(dest))
        if not files:
            raise SenMuseError("任务完成但没有返回素材", job=job)
        self._ledger["jobs"][request_id] = {
            "instance": inst["name"], "job_id": job["id"], "status": "completed",
            "kind": job.get("kind"), "files": files, "md5": md5s, "updated_at": time.time(),
        }
        self._save_ledger()
        return {"job": job, "files": files, "cached": False, "instance": inst["name"]}
```

---

## 四、附：start-senmuse.ps1（服务保活，可选）

服务没跑时自动拉起；放进开机启动文件夹（Win+R 输 `shell:startup`）可开机自启。

```powershell
# SenMuse 服务保活启动脚本（Windows PowerShell）
# 作用：服务没在跑就拉起来（最小化窗口），在跑就什么都不做。
# 用法：
#   1. 手动：右键 → 使用 PowerShell 运行
#   2. 开机自启：Win+R 输入 shell:startup，把本文件的快捷方式放进去
#   3. 定时保活：任务计划程序里建一个每 10 分钟运行本脚本的任务（可选）
#
# 注意：改下面两个路径为你自己的 SenMuse 目录。

$SenMuseDir = "D:\senmuse"
$DataDir = ".senmuse-api"
$HealthUrl = "http://127.0.0.1:47831/healthz"

try {
    $r = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3
    if ($r.alive) {
        Write-Host "SenMuse 已在运行，无需启动。"
        exit 0
    }
} catch {
    # 连不上说明没在跑，继续往下启动
}

Write-Host "SenMuse 未运行，正在启动……"
Start-Process -FilePath "node" `
    -ArgumentList "scripts/senmuse-api.mjs", "serve", "--data", $DataDir `
    -WorkingDirectory $SenMuseDir `
    -WindowStyle Minimized

Start-Sleep -Seconds 3
try {
    $r = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 5
    if ($r.alive) { Write-Host "SenMuse 已启动：http://127.0.0.1:47831" }
} catch {
    Write-Host "启动后仍连不上，请手动在 $SenMuseDir 里运行 serve 看报错。"
}
```
