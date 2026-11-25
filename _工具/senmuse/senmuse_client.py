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
