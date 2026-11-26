# BP-AUTOPULL-20261126-v2 变基合流并开启自动拉取（取代 v1 的停下状态）

- 发起：用户决定（2026-11-26 21:58 CST 选定「变基后把 EP02 一起推到 GitHub」），Muse 直推仓库
- 执行：Hermes / ikun（本地 `D:\Hermes环境准备\AI漫剧制作`，远程 `ai-short-drama-workflow`，公开仓库）
- 背景：v1 执行时 Hermes 只 fetch 后停下，原因是本地 ahead 2 / behind 3 分叉（分叉点 `3f15339`）：本地 `185fa24`、`66aff0c` 两个 EP02 提交未 push，远程 Muse 三个直推提交。文件零重叠。Hermes 停得对，v1 蓝图漏了 ahead 情况。本 v2 是用户对这次分叉的明确处置授权。

## 用户已授权（Hermes 问的 A + 1 + 2 都包含在内）

1. **变基**：把本地 2 个 EP02 提交变基到最新 `origin/main` 之后。这一次豁免 v1 的「不许变基」，仅限这 2 个提交、仅限变基到 `origin/main`，不许交互式改写其他历史。
2. **推 EP02 到 GitHub**：变基后正常 push `main`，EP02 两个提交随之进入公开仓库。用户已知仓库公开并同意。
3. **开自动拉取**：把 `inspect_tick.py` 的 `do_fetch` 默认改 True（Hermes 的第 1 项授权）。
4. **推报告**：写 `reports/RPT-AUTOPULL-20261126-v2.md` 并 push 到远程（Hermes 的第 2 项授权）。

## 仍禁止（没有豁免）

- 不许 `reset --hard`、不许强推（force push）、不许合并提交（merge --no-ff）、不许删文件、不许丢弃任何脏改动。
- 不调模型、不建卡派单、不启用通知、不碰 `engine.py`、不改 `config.env`。只许改 `inspect_tick.py` 的 `do_fetch` 默认值。
- 提交推送只许推：变基后的 EP02 两个提交（随 main push）、报告文件、`.state/flow_state.json`（如需）。不许顺手提交其他生产文件，不许推备份分支。

## 执行顺序

1. **备份**：在当前本地 `main` HEAD 建本地备份分支 `backup-pre-rebase-20261126`，记下分支名和 HEAD。不推这个分支。
2. **脏改动可逆保存**：`git status --porcelain` 列全，逐个记录；已跟踪改动用具名 stash 保存（名字 `autopull-backup-20261126`）；未跟踪文件不动，除非与远程同名文件冲突，冲突先改名备份。保存后确认工作区可变基（干净或只剩不冲突未跟踪项）。
3. **fetch + 变基**：`git fetch` 后 `git rebase origin/main`。预期零冲突；若冲突，立即 `git rebase --abort`，恢复 stash，写报告停下，不强行解决。
4. **验 EP02**：变基后确认 EP02 两个提交的文件都在（校验蓝图、语义校验报告，按实际路径核），记下变基后新提交号。
5. **push**：正常 `git push origin main`（不许 force）。记下推送前后远程 HEAD。若被拒（远程又前进），fetch 后再变基一次再推；第二次仍被拒就停下报告。
6. **开自动拉取**：`inspect_tick.py` 的 `do_fetch` 默认改 True，保持脏/冲突/分叉停下逻辑；`py_compile` 通过；手动跑一次正式模式，确认本地与远程一致时拉取判定正常（up-to-date 或 ff_ok），日志有记录。
7. **等一轮定时巡检**：等 cron `7d225dc62bec` 下一次自动运行，记下时间和结果。不改 cron 参数。
8. **恢复脏改动**：恢复第 2 步 stash，恢复后 `git status` 与第 2 步清单一致（允许多报告文件和 `.state` 文件）。恢复冲突就停下报告，不强行解决。
9. **写报告并推送**：`reports/RPT-AUTOPULL-20261126-v2.md`，包含：备份分支、stash 名、变基前后提交、EP02 文件核验、push 结果、do_fetch 改动、手动运行、定时自动运行、恢复结果、遗留问题。只提交推送报告文件（和 `.state/flow_state.json` 如需）。

## 停下条件

变基冲突、push 第二次被拒、恢复冲突、或脏改动里有判断不了归属的大改动，停下写进报告。报告写完停下等用户下一步。

## 完成标志

本地与远程 `main` 一致，EP02 提交已在 GitHub，定时巡检能自动 ff-only 拉取，脏改动已恢复，报告已推远程。
