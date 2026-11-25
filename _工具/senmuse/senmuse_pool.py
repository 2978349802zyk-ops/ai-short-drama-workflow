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

        # 2b) 提交中状态不明（上次 submit 抛错，服务端可能已建任务）→
        #     只回原实例用同一 request_id 重交（服务端幂等，返回原任务），绝不换实例、绝不回退其他后端
        if entry and entry.get("status") == "submitting":
            inst = next(i for i in self.instances if i["name"] == entry["instance"])
            client = self._client(inst)
            ref_ids = [client.upload_asset(p) for p in (reference_paths or [])]
            job = client.submit(
                request_id=request_id, kind=kind, prompt=prompt,
                reference_ids=ref_ids, aspect=aspect, duration=duration,
                conversation_id=conversation_id,
            )
            entry["job_id"] = job["id"]
            entry["status"] = job.get("status", "submitted")
            entry["updated_at"] = time.time()
            self._save_ledger()
            job = client.wait(job["id"], timeout=wait_timeout)
            return self._finish(request_id, inst, client, job, out_dir, name_prefix)

        # 3) 失败过 → 不自动重试，要求调用方换 attempt
        if entry and entry.get("status") in ("failed", "needs_review", "cancelled"):
            raise SenMuseError(
                f"{request_id} 之前已失败（{entry['status']}），不自动重交；"
                "确认要重生请换 attempt 生成新 request_id",
                job=entry,
            )

        # 4) 新任务 → 选实例；先写 "submitting" 台账再 submit，
        #    这样 submit 抛错（状态不明）时后续调用知道已尝试过、只能回原实例对账
        inst = self._pick_instance()
        client = self._client(inst)
        jobs[request_id] = {
            "instance": inst["name"], "job_id": None, "status": "submitting",
            "kind": kind, "files": [], "md5": [], "updated_at": time.time(),
        }
        self._save_ledger()
        ref_ids = [client.upload_asset(p) for p in (reference_paths or [])]
        job = client.submit(
            request_id=request_id, kind=kind, prompt=prompt,
            reference_ids=ref_ids, aspect=aspect, duration=duration,
            conversation_id=conversation_id,
        )
        jobs[request_id]["job_id"] = job["id"]
        jobs[request_id]["status"] = job.get("status", "submitted")
        jobs[request_id]["updated_at"] = time.time()
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
